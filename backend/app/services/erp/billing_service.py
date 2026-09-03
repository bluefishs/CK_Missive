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

    async def create(self, data: ERPBillingCreate) -> ERPBillingResponse:
        """建立請款 (ADR-0013 Phase 2: 自動生成 billing_code + 併發 retry)"""
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

        規則（刻意簡單）：一次請領、金額＝報價總額、請款日＝今天、pending。分期是人的決定，
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
            if not total or Decimal(str(total)) <= 0:
                return None
            if not getattr(q, "project_code", None) and getattr(q, "status", "") != "confirmed":
                return None
            from sqlalchemy import select as _sel
            existing = (await self.db.execute(_sel(ERPBilling.id).where(ERPBilling.erp_quotation_id == quotation_id).limit(1))).first()
            if existing:
                return None
            created = await self.create(ERPBillingCreate(
                erp_quotation_id=quotation_id,
                billing_period="一次請領",
                billing_date=_date.today(),
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
        """取得報價單所有請款"""
        items = await self.repo.get_by_quotation_id(quotation_id)
        return [ERPBillingResponse.model_validate(b) for b in items]

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
