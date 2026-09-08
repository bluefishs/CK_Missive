"""ERP 請款服務

Version: 2.0.0
- v2.0.0: 收款入帳改為同步 (直接呼叫 ledger_service)，保留 EventBus 通知
- v1.3.0: 收款確認改用 EventBus 解耦 (billing_paid → 帳本入帳)
- v1.2.0: create/delete 改用 Repository 方法 (合規修正)
- v1.1.0: Phase 5-6 收款確認自動寫入 Ledger
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPBilling
from app.repositories.erp import ERPBillingRepository, ERPQuotationRepository
from app.schemas.erp import ERPBillingCreate, ERPBillingUpdate, ERPBillingResponse
from .finance_ledger import FinanceLedgerService
from app.services.audit.mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class ERPBillingService(AuditableServiceMixin):
    """請款管理服務"""

    AUDIT_TABLE = "erp_billings"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPBillingRepository(db)
        self._quotation_repo = ERPQuotationRepository(db)
        self.ledger_service = FinanceLedgerService(db)

    async def _guard_billing_within_contract(
        self, quotation_id: int, new_amount, exclude_billing_id: int | None = None,
    ) -> None:
        """累計開票不得超過合約額 110%（owner 2026-08-29「請加強防呆機制」）。

        實例：CK2026_PM_01_005 的 4 筆請款照 10,560,000 排（多打一個零），
        而合約是 1,056,000 —— 開票排到合約的 10.5 倍，沒有任何一道在問。
        10% 容差涵蓋「total_price 未稅、開票含稅」的既有雙語意（147 未稅/66
        含稅）與尾差；十倍級的輸入錯誤必定被擋。合約額未填（NULL/0）不擋 ——
        那是 A36 那一族的問題，由週稽核盯，不在這裡誤傷。
        """
        from decimal import Decimal
        from sqlalchemy import select as _sel, func as _fn

        quotation = await self._quotation_repo.get_by_id(quotation_id)
        total = getattr(quotation, "total_price", None) if quotation else None
        if not total or Decimal(str(total)) <= 0:
            return
        stmt = _sel(_fn.coalesce(_fn.sum(ERPBilling.billing_amount), 0)).where(
            ERPBilling.erp_quotation_id == quotation_id)
        if exclude_billing_id is not None:
            stmt = stmt.where(ERPBilling.id != exclude_billing_id)
        existing_sum = Decimal(str(await self.db.scalar(stmt) or 0))
        cumulative = existing_sum + Decimal(str(new_amount or 0))
        limit = Decimal(str(total)) * Decimal("1.10")
        if cumulative > limit:
            raise ValueError(
                f"累計開票 NT$ {int(cumulative):,} 已超過合約額 NT$ {int(Decimal(str(total))):,} "
                f"的 110% —— 請先確認合約額或既有請款是否有誤。"
                f"（本筆 NT$ {int(Decimal(str(new_amount or 0))):,}，"
                f"既有 {int(existing_sum):,}）"
            )

    async def _sync_ledger_if_paid(self, billing) -> None:
        """已收款 → 同步統一帳本（冪等）。

        2026-08-17：抽成共用方法。原本這段**只寫在 `update` 裡**，
        於是「建立時就標已收款」那條路徑永遠不會入帳 ——
        owner 回報「為何無對應帳本」正是這個（實測全庫 1 筆卡在這）。

        同時移除了原本的 `old_status != "paid"` 條件：它的用意是
        「只在狀態轉換那一刻入帳」，但**冪等已由 find_by_source 擔保**，
        那個條件不提供任何保護，只製造盲區。

        帳本是「專案財務 → 公司 ERP」的接點 —— 缺一筆不只是這一案看不到，
        是公司層彙總少了這一筆。
        """
        if billing.payment_status != "paid" or not billing.payment_amount:
            return
        existing = await self.ledger_service.find_by_source("erp_billing", billing.id)
        if existing:
            logger.warning("帳本已有 erp_billing/%d 的 entry，跳過重複入帳", billing.id)
            return
        case_code = await self._get_case_code(billing.erp_quotation_id)
        await self.ledger_service.record_from_billing(
            billing_id=billing.id,
            case_code=case_code,
            payment_amount=billing.payment_amount,
            payment_date=billing.payment_date,
            billing_period=billing.billing_period,
        )
        logger.info(
            "AR 同步入帳: 請款 #%d, 金額 %s, 案號 %s",
            billing.id, billing.payment_amount, case_code,
        )

    async def sync_ledger_by_id(self, billing_id: int) -> bool:
        """給**繞過本服務的寫入路徑**用的正式入帳入口（2026-09-08）。

        背景：總表匯入器用裸 SQL 把第一筆請款標成 paid
        （`UPDATE erp_billings SET payment_status='paid' ...`）⇒ `_sync_ledger_if_paid`
        從未執行 ⇒ **20 筆已收款、637,286 元從來沒有進統一帳本**，而每日對帳
        因此天天報 AR 差異。同型的 AP 兩筆（政威 id 72/73）08-29 就被點名，
        程式碼修了、存量沒回填，於是又響了 10 天。

        ⇒ 形狀是「主路徑有守衛、第二條路徑沒接上」。與其禁止裸 SQL
        （匯入本來就需要批次更新），不如**給它一個必須呼叫的入口**。
        回傳是否真的新增了分錄。冪等由 `_sync_ledger_if_paid` 的 find_by_source 擔保。
        """
        from sqlalchemy import select as _select
        from app.extended.models.erp import ERPBilling
        b = (await self.db.execute(
            _select(ERPBilling).where(ERPBilling.id == billing_id))).scalar_one_or_none()
        if b is None:
            logger.warning("sync_ledger_by_id: 找不到請款 #%s", billing_id)
            return False
        before = await self.ledger_service.find_by_source("erp_billing", b.id)
        await self._sync_ledger_if_paid(b)
        return before is None

    async def create(self, data: ERPBillingCreate) -> ERPBillingResponse:
        """建立請款 (ADR-0013 Phase 2: 自動生成 billing_code + 併發 retry)"""

        # 2026-09-07：`billing_date` 改為可空是**為了自動建立的佔位**（沒有請款就沒有請款日期）。
        # 人工建立的請款仍然必須有日期 —— 少了它，那筆在逾期名單上會退回用報價單日期算，
        # 而人工建的請款本來就有一個真實的請款日，用報價日當錨點是錯的。
        # 判準：備註不是系統自動建立的那一種，就要求日期（填報當下擋，不留給事後稽核）。
        if not data.billing_date and not (data.notes or "").startswith(self.AUTO_FIRST_NOTE):
            raise ValueError("請填寫請款日期（僅系統自動建立的第一期可留白）")
        from datetime import datetime
        from app.services.contract import CaseCodeService
        from app.services.coding_helpers import retry_on_code_conflict

        # ── 「已收款」必須有金額（2026-08-17 補 create 端）─────────────────
        #
        # 08-16 我在 `update` 加了這道守衛，**但沒掃 create** ——
        # 而這 15 筆失真資料正是**建立時就直接帶 payment_status='paid'** 進來的，
        # 於是繞過守衛存下「狀態說已收、金額是空的」這個矛盾狀態。
        # 後果：統計卡「已收款額」顯示 **0**，而請款總額 3,383 萬。
        #
        # 這是 L83 家族（修一處沒掃同型）——同一條規則要在**所有寫入路徑**上。
        if data.payment_status == "paid" and not getattr(data, "payment_amount", None):
            raise ValueError(
                "建立時標記為「已收款」必須同時填寫收款金額 —— "
                "否則統計會顯示「請款 N 元、已收 0 元」而看不出是資料缺失。"
                "（若尚未收款，狀態請留「待收款」）"
            )
        # 2026-08-29（P2-6）：paid 也要有日期 —— 實測 2 筆 paid 缺 payment_date
        # （id 63/95，正是重複入帳那兩筆），入帳落 date.today() 使交易日期失真
        if data.payment_status == "paid" and not getattr(data, "payment_date", None):
            raise ValueError(
                "建立時標記為「已收款」必須同時填寫收款日期 —— "
                "缺日期會讓帳本的交易日期失真為入帳當天。"
            )

        # ── 防重（2026-08-17 owner：「沒防呆 新增超過 10 筆紀錄」）──────────
        #
        # 實測報價 152 有 **15 筆完全相同**的請款（同日期、同金額 2,249,163、
        # 同期別）。成因是同日修好的那個交易層缺陷：
        # `repo.create` 已經 commit 成功，才在 `sp.commit()` 拋
        # ResourceClosedError → **資料存進去了但畫面說失敗** → 使用者重試 → 再存一筆。
        #
        # 那個缺陷已修，但**防重是獨立的必要條件**：
        # 網路重送、連點兩下、瀏覽器重整都會造成同樣結果，
        # 而請款是金額紀錄 —— 重複一筆就是帳目多一筆應收。
        #
        # 判準＝同報價 ＋ 同請款日期 ＋ 同金額。刻意**不看期別**：
        # 期別可留空（實測 16 筆 pending 全為空），把可空欄位放進判準
        # 會讓兩筆都沒填期別時無法比對 —— 那正是「防重防不到」的來源。
        from sqlalchemy import and_, select as _sel

        dup = (await self.db.execute(
            _sel(ERPBilling).where(and_(
                ERPBilling.erp_quotation_id == data.erp_quotation_id,
                ERPBilling.billing_date == data.billing_date,
                ERPBilling.billing_amount == data.billing_amount,
            )).limit(1)
        )).scalars().first()
        if dup:
            raise ValueError(
                f"已有相同的請款紀錄（{dup.billing_code}：{data.billing_date} "
                f"NT$ {int(data.billing_amount):,}）。"
                "若確實需要同日同額的第二筆，請在期別或備註標明差異後再送出。"
            )

        # 2026-08-29 owner：「請加強防呆機制」—— 累計開票 vs 合約額
        await self._guard_billing_within_contract(
            data.erp_quotation_id, data.billing_amount)

        async def _create_op() -> ERPBilling:
            dump = data.model_dump()
            if not dump.get("billing_code"):
                code_svc = CaseCodeService(self.db)
                dump["billing_code"] = await code_svc.generate_billing_code(
                    year=datetime.now().year
                )
            # 2026-08-17：**必須 auto_commit=False**。
            # 這裡跑在 `retry_on_code_conflict` 的 SAVEPOINT 內，
            # 而 `BaseRepository.create` 預設 `auto_commit=True` 會直接 commit
            # → 外層交易被關掉 → `sp.commit()` 拋
            # `ResourceClosedError: This transaction is closed`
            # → 使用者看到「新增紀錄失敗」（owner 2026-08-17 於
            # /erp/quotations/152/accounts/receivable/create 回報）。
            #
            # 對照組：`asset_service` 用的 `create_asset` 只 flush、
            # 由外層自己 commit —— 那才是 savepoint 內該有的寫法。
            billing = await self.repo.create(dump, auto_commit=False)
            await self.audit_create(billing.id, dump)
            return billing

        billing = await retry_on_code_conflict(
            self.db, _create_op, unique_field="billing_code"
        )
        # 建立時就標「已收款」也要入帳 —— 見 _sync_ledger_if_paid 的說明。
        await self._sync_ledger_if_paid(billing)

        # savepoint commit 只是釋放 SAVEPOINT，**外層交易仍未落地** ——
        # 少了這一行會變成「不報錯但資料沒存進去」，比原本的錯誤更糟
        # （使用者以為成功了）。asset_service 的寫法就是這樣：
        # retry_on_code_conflict 之後自己 commit。
        await self.db.commit()
        return ERPBillingResponse.model_validate(billing)

    AUTO_FIRST_NOTE = "系統自動建立：成案即應收（一次請領，金額＝報價總額）"

    async def ensure_first_period(self, quotation_id: int, *, reason: str = "") -> Optional[ERPBillingResponse]:
        """成案即應收：報價單有總額、已成案、還沒有任何請款 ⇒ 自動建第一筆（owner 2026-09-03）。

        為什麼一定要有這一筆：夜間吹哨者的「請款逾期」只看 erp_billings，沒有請款的案子
        **永遠不會被催** —— 09-03 量到 90 張成案有金額卻無請款（3,109 萬），稽催鏈對它們是啞的。

        規則（刻意簡單）：一次請領、金額＝報價總額、**請款日留白**（2026-09-07：
        原為今天 → 報價單日期 → 留白）、pending。分期是人的決定，
        由承辦在請款頁把這一筆改期別／拆金額；系統只保證「有東西可催」。
        不建的情況：無總額（要人填，weekly 103 YELLOW）／未成案／已有任何請款。
        失敗只記 log 不 raise —— 案件比這一筆重要（同 promote 內的承辦承接）。
        """
        from datetime import date as _date
        from decimal import Decimal
        try:
            q = await self._quotation_repo.get_by_id(quotation_id)
            if not q or q.deleted_at is not None:
                return None
            total = getattr(q, "total_price", None)
            # 2026-09-04 晚：有議價金額的案，第一期＝承攬金額（議價後的實際金額），不是投標報價
            if getattr(q, "case_code", None):
                from sqlalchemy import text as _t
                won = (await self.db.execute(_t(
                    "SELECT NULLIF(winning_amount, 0) FROM contract_projects WHERE case_code = :c LIMIT 1"
                ), {"c": q.case_code})).scalar()
                if won is not None:
                    total = won
            if not total or Decimal(str(total)) <= 0:
                return None
            if not getattr(q, "project_code", None) and getattr(q, "status", "") != "confirmed":
                return None
            from sqlalchemy import select as _sel
            existing = (await self.db.execute(_sel(ERPBilling.id).where(ERPBilling.erp_quotation_id == quotation_id).limit(1))).first()
            if existing:
                return None
            # ⚠️ 2026-09-07 owner：「原自動填列請款日期機制改為報價單日期辦理稽催，
            #    避免誤解 09/03 真的已辦理請款作業」。
            #
            # 原本填**今天** —— 那是「系統建立這筆的日子」，不是任何人做過的事。
            # 畫面上它長得跟真的請款日期一模一樣，於是 09/03 成案的案子看起來像
            # 09/03 就請過款了。這一筆本來只是「有東西可催」的佔位，不該宣稱一個動作。
            #
            # 2026-09-07（owner 第二次指正）：**留白**。
            # 先前改成報價單日期仍有同一個毛病 —— 畫面上它與真的請款日期長得一模一樣，
            # 「這個案請過款了嗎」看畫面得到的答案還是錯的。
            # 沒有請款就沒有請款日期。稽催改用 COALESCE(請款日, 報價單日期)，不會失效。
            created = await self.create(ERPBillingCreate(
                erp_quotation_id=quotation_id,
                billing_period="一次請領",
                billing_date=None,
                billing_amount=Decimal(str(total)),
                payment_status="pending",
                notes=f"{self.AUTO_FIRST_NOTE}{'；' + reason if reason else ''}",
            ))
            logger.info("成案即應收：自動建第一期 quotation=%s amount=%s (%s)", quotation_id, total, reason)
            return created
        except Exception as e:
            logger.error("成案即應收自動建第一期失敗 quotation=%s: %s", quotation_id, e, exc_info=True)
            return None

    async def get_by_quotation(self, quotation_id: int) -> List[ERPBillingResponse]:
        """取得報價單所有請款（帶關聯發票號）。

        2026-09-04 owner「/erp/quotations/167?tab=receivable 有已開立發票但前端無顯示」：
        回應 schema 早有 `invoice_number`，這裡從沒填 ⇒ 畫面永遠沒有、「開立發票」鈕照樣出現、再按就 400「已有關聯發票」。
        schema 有欄位不等於有人在填（同 09-04 財務摘要四欄）。
        """
        from sqlalchemy import select
        from app.extended.models.erp import ERPInvoice
        items = await self.repo.get_by_quotation_id(quotation_id)
        ids = [b.id for b in items]
        inv_by_billing: dict[int, tuple] = {}
        if ids:
            rows = (await self.db.execute(
                select(ERPInvoice.billing_id, ERPInvoice.id, ERPInvoice.invoice_number, ERPInvoice.invoice_date, ERPInvoice.amount, ERPInvoice.tax_amount)
                .where(ERPInvoice.billing_id.in_(ids), ERPInvoice.status != "voided").order_by(ERPInvoice.id)
            )).all()
            for bid, iid, no, dt, amt, tax in rows:
                inv_by_billing.setdefault(bid, (iid, no, dt, amt, tax))
        # 報價單日期：自動建立的第一期用它當時間錨點（09-07），畫面也要看得到
        from app.extended.models.erp import ERPQuotation as _Q
        quoted_at = (await self.db.execute(
            select(_Q.quoted_at).where(_Q.id == quotation_id)
        )).scalar()

        out = []
        for b in items:
            r = ERPBillingResponse.model_validate(b)
            r.quoted_at = quoted_at
            inv = inv_by_billing.get(b.id)
            if inv:
                (r.invoice_id, r.invoice_number, r.invoice_date,
                 r.invoice_amount, r.invoice_tax_amount) = inv
            out.append(r)
        return out

    async def update(self, billing_id: int, data: ERPBillingUpdate) -> Optional[ERPBillingResponse]:
        """更新請款 (含收款狀態) — 收款確認時自動入帳"""
        billing = await self.repo.get_by_id(billing_id)
        if not billing:
            return None

        old_status = billing.payment_status
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(billing, key, value)

        # 2026-08-16：「已收款」必須有金額。
        #
        # 入帳條件本來就要求 `billing.payment_amount`，但**存檔時沒有擋** ——
        # 於是可以存下「狀態說已付、金額是空的」這個矛盾狀態，
        # 而它不會報錯、不會入帳，只是安靜地讓帳本少一筆。
        # 實測當天有 2 筆（BL_2026_049/050）正是如此。
        #
        # 擋在 service 而不是 schema：金額與狀態可能分兩次請求送，
        # schema 只看得到單次 payload，看不到最終狀態。
        # 2026-09-07：互抵／不開票必須說得出依據 —— 否則「已收款卻沒有發票」與
        # 「該開票卻漏開」在系統裡長得一樣，稽核只能兩者都報或兩者都不報。
        _st = getattr(billing, "settlement_type", None) or "invoice"
        if _st in ("offset", "no_invoice") and not (getattr(billing, "settlement_note", None) or "").strip():
            raise ValueError(
                "結算方式為「互抵」或「約定不開票」時必須填寫依據（與哪一筆應付互抵／依據哪一份約定）"
                " —— 沒有依據的不開票，事後無法與漏開發票分辨。"
            )

        # 2026-09-07 owner：「收款在填報時就要有檢核」。收款額不得超過請款額 ——
        # 超過的那一刻起，「應收未收」會變成負數而報表上看不出是哪一筆造成的。
        # 容差 1 元（四捨五入）；真的多收要先改請款額（追加）再登收款。
        from decimal import Decimal as _D
        _pay = billing.payment_amount
        if _pay is not None and billing.billing_amount is not None:
            if _D(str(_pay)) - _D(str(billing.billing_amount)) > 1:
                raise ValueError(
                    f"收款 {_D(str(_pay)):,.0f} 超過請款額 {_D(str(billing.billing_amount)):,.0f}"
                    f"（{billing.billing_period or ''}）—— 若確實多收，請先調整請款額再登錄收款。"
                )
        if billing.payment_status == "paid" and not billing.payment_amount:
            raise ValueError(
                "標記為「已收款」時必須填寫收款金額 —— "
                "沒有金額就無法入帳，帳本會少這一筆。"
                "若尚未收到款，請維持「待收款」。"
            )
        # 2026-08-29（P2-6）：與 create 端同判準（L83：同一條規則掃所有寫入路徑）
        # ⚠️ 2026-08-29 修正過度嚴格：原本只看「最終狀態是 paid 且沒有日期」，
        # 於是**連只改備註的既有紀錄也擋** —— 而系統裡確實有缺日期的存量
        # （同日查出 billing 63/95、payables 72/73 共 4 筆，那是資料問題、
        #  需要 owner 提供真實日期，不是我能編的）。
        # 我的驗證會讓那些紀錄**再也無法編輯**，包括補上日期本身以外的任何欄位。
        # ⇒ 只在這次更新**真的碰到付款欄位**時才擋（新設為 paid、或改動日期）。
        #   存量的不一致由對帳與 weekly 檢核處理，不是靠讓人改不了東西。
        _touched_payment = bool(
            {"payment_status", "payment_date", "payment_amount"} & set(update_data)
        )
        if _touched_payment and billing.payment_status == "paid" and not billing.payment_date:
            raise ValueError(
                "標記為「已收款」時必須填寫收款日期 —— "
                "缺日期會讓帳本的交易日期失真為入帳當天。"
            )
        # 2026-08-29 owner 防呆：更新金額也要過合約上限（L83 同型掃描）
        await self._guard_billing_within_contract(
            billing.erp_quotation_id, billing.billing_amount,
            exclude_billing_id=billing.id)

        await self.db.flush()
        await self.db.refresh(billing)

        await self._sync_ledger_if_paid(billing)

        await self.db.commit()
        await self.audit_update(billing_id, update_data)

        # EventBus 通知 (非關鍵路徑 — 用於通知推播，失敗不影響帳本)
        # ⚠️ 2026-08-17：我把入帳段抽成 `_sync_ledger_if_paid` 時，
        # 連同 `new_status = billing.payment_status` 這行一起刪掉了，
        # 而這裡還在用它 → NameError（實測當場踩到）。
        # **抽共用方法時要檢查被刪的區塊裡有沒有別人在用的變數。**
        #
        # EventBus 這裡**保留** old_status 條件：推播的語意就是「狀態剛剛改變」，
        # 重複推播是騷擾（與入帳不同 —— 入帳的冪等由 find_by_source 擔保）。
        if billing.payment_status == "paid" and old_status != "paid":
            try:
                from app.core.event_bus import EventBus
                from app.core.domain_events import billing_paid
                bus = EventBus.get_instance()
                await bus.publish(billing_paid(
                    billing_id=billing.id,
                    amount=float(billing.payment_amount or 0),
                    case_code=await self._get_case_code(billing.erp_quotation_id),
                    payment_date=str(billing.payment_date) if billing.payment_date else None,
                    billing_period=billing.billing_period,
                ))
            except Exception as e:
                logger.debug("billing_paid event publish skipped: %s", e)

        return ERPBillingResponse.model_validate(billing)

    async def delete(self, billing_id: int) -> bool:
        """刪除請款 — 同步清理對應帳本 entries"""
        # 先清理帳本孤兒
        await self.ledger_service.delete_by_source("erp_billing", billing_id)
        result = await self.repo.delete(billing_id)
        if result:
            await self.audit_delete(billing_id)
        return result

    async def _get_case_code(self, quotation_id: int) -> str:
        """從報價單取得 case_code"""
        quotation = await self._quotation_repo.get_by_id(quotation_id)
        return quotation.case_code if quotation and quotation.case_code else "一般營運"
