"""ERP 廠商應付服務

Version: 1.2.0
- v1.2.0: create/delete 改用 Repository 方法 (合規修正)
- v1.1.0: 付款確認時自動寫入 FinanceLedger (AP 自動拋轉)
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPVendorPayable
from app.repositories.erp import ERPVendorPayableRepository, ERPQuotationRepository
from app.repositories.vendor_repository import VendorRepository
from app.schemas.erp import ERPVendorPayableCreate, ERPVendorPayableUpdate, ERPVendorPayableResponse
from .finance_ledger import FinanceLedgerService
from app.services.audit.mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class ERPVendorPayableService(AuditableServiceMixin):
    """廠商應付管理服務"""

    AUDIT_TABLE = "erp_vendor_payables"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPVendorPayableRepository(db)
        self._quotation_repo = ERPQuotationRepository(db)
        self._vendor_repo = VendorRepository(db)
        self.ledger_service = FinanceLedgerService(db)

    async def _sync_ledger_if_paid(self, payable) -> None:
        """已付款 → 同步統一帳本（冪等＋金額校正）。

        2026-08-29 財務域複查 P0-2：AP 差額 1,060,000 的三筆全是這裡的缺口——
        ① `create` 路徑**完全沒有**入帳同步 ⇒ 建立時就標 paid 的（id 72/73，
           各 500,000）永遠不入帳——與 billing 08-17 修掉的是同一型；
        ② `update` 只在「非 paid → paid」轉換那一刻入帳 ⇒ 已 paid 後改金額
           （id 69：900,000 → 960,000）帳本不會跟。
        修法同 billing `_sync_ledger_if_paid`：冪等由 find_by_source 擔保、
        不設轉換條件；另加**金額校正**——既有 entry 金額與現值不符時更新
        （billing 端零筆不符所以不需要；AP 端實測有）。
        """
        if payable.payment_status != "paid" or not payable.paid_amount:
            return
        existing = await self.ledger_service.find_by_source("erp_vendor_payable", payable.id)
        if existing:
            from decimal import Decimal
            paid = Decimal(str(payable.paid_amount))
            if existing.amount != paid:
                logger.info(
                    "AP 帳本金額校正: 應付 #%d %s -> %s",
                    payable.id, existing.amount, paid,
                )
                existing.amount = paid
                if payable.paid_date:
                    existing.transaction_date = payable.paid_date
            return
        case_code = await self._get_case_code(payable.erp_quotation_id)
        if not case_code:
            logger.error(
                "AP 入帳失敗：應付 #%d 找不到案號（報價 %s）",
                payable.id, payable.erp_quotation_id,
            )
            return
        await self.ledger_service.record_from_vendor_payable(
            payable_id=payable.id,
            case_code=case_code,
            paid_amount=payable.paid_amount,
            paid_date=payable.paid_date,
            vendor_name=payable.vendor_name,
            description=payable.description,
            vendor_id=payable.vendor_id,
        )
        logger.info(
            "AP 自動入帳: 廠商 %s, 金額 %s, 案號 %s",
            payable.vendor_name, payable.paid_amount, case_code,
        )

    async def create(self, data: ERPVendorPayableCreate) -> ERPVendorPayableResponse:
        """建立廠商應付 — 自動由 vendor_code 或 vendor_name 配對 vendor_id"""
        # ── 防重（2026-08-17）────────────────────────────────────────────
        # 與請款同型（見 billing_service.create 的說明）。
        # 實測 CK2026_PM_01_005 已有兩筆同廠商同金額的應付（id 65/66）。
        #
        # 判準＝同報價 ＋ 同廠商 ＋ 同金額 ＋ **同期別**。不看 due_date（可空）。
        #
        # ⚠️ 2026-08-18 修正：原本沒有期別這一項，於是**分期付款被擋住** ——
        # owner 在 `/erp/quotations/161/accounts/payable/create` 撞到 400，
        # 而該報價已有一筆「金粟科技 900,000 第一期」，要新增的是第二期。
        #
        # 同廠商、同金額、不同期別**是分期付款的正常樣貌**，不是重複。
        # 我 08-18 稍早才補上 `payable_period` 欄位，卻沒同步這個判準 ——
        # **加了新欄位就要問：有哪些既有邏輯應該把它算進去？**
        #
        # 兩筆都沒填期別時仍會被擋（NULL = NULL 在 SQL 裡不成立，
        # 所以用 IS NOT DISTINCT FROM 讓「都沒填」也視為相同）——
        # 那才是真正無法分辨的情況，而訊息已經告訴使用者怎麼區分。
        from sqlalchemy import and_, select as _sel

        dup = (await self.db.execute(
            _sel(ERPVendorPayable).where(and_(
                ERPVendorPayable.erp_quotation_id == data.erp_quotation_id,
                ERPVendorPayable.vendor_name == data.vendor_name,
                ERPVendorPayable.payable_amount == data.payable_amount,
                ERPVendorPayable.payable_period.is_not_distinct_from(
                    data.payable_period
                ),
            )).limit(1)
        )).scalars().first()
        if dup:
            same_period = f"（{data.payable_period}）" if data.payable_period else ""
            raise ValueError(
                f"已有相同的應付紀錄{same_period}：{data.vendor_name} "
                f"NT$ {int(data.payable_amount):,}。"
                "若這是不同期的款項，請填「期別」；"
                "若確實是同期的第二筆，請在說明或發票號碼標明差異後再送出。"
            )

        create_data = data.model_dump()
        # 自動配對 vendor_id: 優先 vendor_code，其次 vendor_name 模糊匹配
        if not create_data.get("vendor_id"):
            resolved = await self._resolve_vendor_id(
                vendor_code=create_data.get("vendor_code"),
                vendor_name=create_data.get("vendor_name"),
            )
            if resolved:
                create_data["vendor_id"] = resolved
        # 建立時就標 paid 也要擋「沒金額／沒日期」—— 與 update 同判準
        if create_data.get("payment_status") == "paid":
            if not create_data.get("paid_amount"):
                raise ValueError(
                    "標記為「已付款」時必須填寫付款金額 —— 沒有金額就無法入帳。"
                )
            if not create_data.get("paid_date"):
                raise ValueError(
                    "標記為「已付款」時必須填寫付款日期 —— "
                    "缺日期會讓帳本的交易日期失真為入帳當天。"
                )
        payable = await self.repo.create(create_data)
        # 建立時就標「已付款」也要入帳（P0-2 ①：這條路徑原本完全沒有同步）
        await self._sync_ledger_if_paid(payable)
        await self.audit_create(payable.id, create_data)
        return ERPVendorPayableResponse.model_validate(payable)

    async def _canonical_vendor_names(self, items: list) -> dict:
        """vendor_id → partner_vendors 的現行名稱（批次一次查，避免 N+1）。

        owner 2026-08-27：「**廠商身分統一為單一來源**」。

        應付單自存一份 `vendor_name` 文字，而 FK 指向 `partner_vendors`
        ⇒ **同一件事兩個來源**。2026-08-27 實測已有 3 筆對不上：

            應付#47  自存「竣吉不動產估價師」        vs FK「竣吉不動產估價師事務所」
            應付#39  自存「林晉廷」                  vs FK「林宥廷測量技師事務所」
            應付#51  自存「銢欣有限公司乃耳企業社」   vs FK「銢欣有限公司」

        ⚠️ 它們**不是配對配錯的**：`_resolve_vendor_id` 是**精確**比對
        （`find_one_by(vendor_name=...)`，儘管上面的註解寫「模糊匹配」——
        註解與實作不一致，我一度採信了註解）。
        真正的成因是**先配對成功、之後 `partner_vendors.vendor_name` 被改**，
        而應付單那份文字沒跟著改 —— 典型的「快照 vs 引用」。

        ⇒ 有 `vendor_id` 時**一律以 FK 為準**；自存的舊值留在 DB 不動
        （那是歷史，改它要 owner 決定哪個對，見 V5）。
        """
        ids = {p.vendor_id for p in items if getattr(p, "vendor_id", None)}
        if not ids:
            return {}
        rows = await self._vendor_repo.get_by_ids(list(ids))
        return {v.id: v.vendor_name for v in rows if v.vendor_name}

    def _with_canonical_name(self, payable, names: dict) -> ERPVendorPayableResponse:
        resp = ERPVendorPayableResponse.model_validate(payable)
        canonical = names.get(getattr(payable, "vendor_id", None))
        if canonical and canonical != resp.vendor_name:
            # 兩個都保留 —— 見 schema 的說明：靜靜蓋掉會讓「FK 才是錯的」
            # 那一種情況永遠沒有人發現
            resp.vendor_name_recorded = resp.vendor_name
            resp.vendor_name = canonical
        return resp

    async def get_by_quotation(self, quotation_id: int) -> List[ERPVendorPayableResponse]:
        """取得報價單所有應付（廠商名以 FK 為單一來源）"""
        items = await self.repo.get_by_quotation_id(quotation_id)
        names = await self._canonical_vendor_names(items)
        return [self._with_canonical_name(p, names) for p in items]

    async def update(self, payable_id: int, data: ERPVendorPayableUpdate) -> Optional[ERPVendorPayableResponse]:
        """更新廠商應付 — 付款確認時自動寫入帳本

        狀態由非 paid → paid 時，自動呼叫 FinanceLedgerService 記錄支出。
        已經是 paid 狀態時不重複入帳。
        """
        payable = await self.repo.get_by_id(payable_id)
        if not payable:
            return None

        old_status = payable.payment_status
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(payable, key, value)

        # 2026-08-16：與請款同型的守衛（請款那邊實測有 2 筆矛盾狀態）。
        # 拋轉條件本來就要求 paid_amount，但存檔時不擋 ——
        # 「狀態說已付、金額是空的」會安靜地讓帳本少一筆。
        if payable.payment_status == "paid" and not payable.paid_amount:
            raise ValueError(
                "標記為「已付款」時必須填寫付款金額 —— "
                "沒有金額就無法入帳，帳本會少這一筆。"
                "若尚未付款，請維持「未付款」。"
            )
        # 2026-08-29（P2-6 同型）：paid 也要有日期 —— 缺日期時入帳
        # 落 date.today()，交易日期失真為入帳當天
        # ⚠️ 2026-08-29 修正過度嚴格：原本只看「最終狀態是 paid 且沒有日期」，
        # 於是**連只改備註的既有紀錄也擋** —— 而系統裡確實有缺日期的存量
        # （同日查出 billing 63/95、payables 72/73 共 4 筆，那是資料問題、
        #  需要 owner 提供真實日期，不是我能編的）。
        # 我的驗證會讓那些紀錄**再也無法編輯**，包括補上日期本身以外的任何欄位。
        # ⇒ 只在這次更新**真的碰到付款欄位**時才擋（新設為 paid、或改動日期）。
        #   存量的不一致由對帳與 weekly 檢核處理，不是靠讓人改不了東西。
        _touched_payment = bool(
            {"payment_status", "paid_date", "payment_amount"} & set(update_data)
        )
        if _touched_payment and payable.payment_status == "paid" and not payable.paid_date:
            raise ValueError(
                "標記為「已付款」時必須填寫付款日期 —— "
                "缺日期會讓帳本的交易日期失真為入帳當天。"
            )

        await self.db.flush()
        await self.db.refresh(payable)

        # AP 自動拋轉（2026-08-29 改）：移除「非 paid → paid」轉換條件 ——
        # 冪等由 _sync_ledger_if_paid 的 find_by_source 擔保，轉換條件不提供
        # 保護、只讓「已 paid 後改金額」永遠不同步（P0-2 ②，id 69 實例）。
        # old_status 保留給 audit 語意（此處不再使用）。
        _ = old_status
        await self._sync_ledger_if_paid(payable)

        await self.db.commit()
        await self.audit_update(payable_id, update_data)
        return ERPVendorPayableResponse.model_validate(payable)

    async def _get_case_code(self, quotation_id: int) -> Optional[str]:
        """透過報價單取得案號"""
        quotation = await self._quotation_repo.get_by_id(quotation_id)
        return quotation.case_code if quotation else None

    async def _resolve_vendor_id(
        self, vendor_code: Optional[str] = None, vendor_name: Optional[str] = None,
    ) -> Optional[int]:
        """由 vendor_code 或 vendor_name 查找 partner_vendors.id

        優先順序：vendor_code 精確匹配 > vendor_name 精確匹配
        """
        if vendor_code:
            vendor = await self._vendor_repo.find_one_by(vendor_code=vendor_code)
            if vendor:
                return vendor.id
        if vendor_name:
            vendor = await self._vendor_repo.find_one_by(vendor_name=vendor_name)
            if vendor:
                logger.info("vendor_id 自動解析: '%s' → vendor #%d", vendor_name, vendor.id)
                return vendor.id
        return None

    # ── 2026-09-04 owner「/contract-cases/191?tab=vendors 已增列費用，但 /erp/vendor-accounts 沒列入、
    #    /erp/quotations/172?tab=payable 也沒自動填報」──
    # 承攬案的「協力廠商」分頁寫的是 project_vendor_association（vendor_id + contract_amount），
    # 而廠商帳款／應付分頁讀的是 erp_vendor_payables（掛 erp_quotation_id）。兩張表沒有橋：
    # 實測 16 案有指派、13 案沒有對應應付。與「成案即應收」（ensure_first_period）同型：指派即應付。
    AUTO_TAG = "[auto:vendor_association]"

    async def ensure_from_association(
        self, project_id: int, vendor_id: int, contract_amount, role: Optional[str] = None,
    ) -> Optional[ERPVendorPayable]:
        """協力廠商指派 → 對應報價單的應付（沒有就建、自動建的且未付就跟著改金額）。

        回 None 的情況：金額空／0、承攬案沒有報價單（GN 標案）、找不到廠商。都會 logger.info 出聲。
        只動自己建的（notes 帶 AUTO_TAG）且尚未付款的；人工建的應付不碰。
        """
        from decimal import Decimal
        from sqlalchemy import select as _sel
        from app.extended.models.core import ContractProject, PartnerVendor
        from app.extended.models.erp import ERPQuotation

        amount = Decimal(str(contract_amount or 0))
        cp = (await self.db.execute(_sel(ContractProject).where(ContractProject.id == project_id))).scalar_one_or_none()
        vendor = (await self.db.execute(_sel(PartnerVendor).where(PartnerVendor.id == vendor_id))).scalar_one_or_none()
        if cp is None or vendor is None:
            logger.info("ensure_from_association: 承攬案 %s 或廠商 %s 不存在，略過", project_id, vendor_id)
            return None
        q = (await self.db.execute(
            _sel(ERPQuotation)
            # 不排除 quote_kind=tender：01 委辦招標案的應付本來就掛在那張投標報價單上
            # （#189 的 10,560,000 就是 tender；首版排除它讓 187／189 四筆 2,000,000 指派全被略過）
            .where(ERPQuotation.case_code == cp.case_code, ERPQuotation.deleted_at.is_(None))
            .order_by((ERPQuotation.project_code == cp.project_code).desc(), ERPQuotation.id.desc())
            .limit(1)
        )).scalar_one_or_none()
        if q is None:
            logger.info("ensure_from_association: 承攬案 %s（%s）沒有報價單，應付無處可掛（GN 標案豁免，weekly 98）", project_id, cp.case_code)
            return None
        existing = (await self.db.execute(
            _sel(ERPVendorPayable)
            .where(ERPVendorPayable.erp_quotation_id == q.id)
            .where((ERPVendorPayable.vendor_id == vendor_id) | (ERPVendorPayable.vendor_name == vendor.vendor_name))
            .order_by(ERPVendorPayable.id)
        )).scalars().all()
        auto = [p for p in existing if (p.notes or "").startswith(self.AUTO_TAG)]
        if existing and not auto:
            # 人工已建應付 ⇒ 指派金額只是參考，不覆蓋人工紀錄
            return existing[0]
        if auto:
            p = auto[0]
            unpaid = (p.payment_status or "unpaid") in ("unpaid", "pending") and not (p.paid_amount or 0)
            if amount <= 0 and unpaid:
                await self.repo.delete(p.id)
                await self.audit_delete(p.id)
                return None
            if unpaid and Decimal(str(p.payable_amount or 0)) != amount:
                p.payable_amount = amount
                p.description = role or p.description
                await self.db.commit()
                await self.audit_update(p.id, {"payable_amount": str(amount)})
            return p
        if amount <= 0:
            return None
        payable = await self.repo.create({
            "erp_quotation_id": q.id,
            "vendor_id": vendor.id,
            "vendor_name": vendor.vendor_name,
            "vendor_code": vendor.tax_id or vendor.vendor_code,
            "payable_amount": amount,
            "description": role or "協力廠商指派",
            "payment_status": "unpaid",
            "notes": f"{self.AUTO_TAG} 由承攬案「協力廠商」分頁的指派自動建立（{cp.project_code or cp.case_code}）",
        })
        await self.audit_create(payable.id, {"erp_quotation_id": q.id, "vendor_id": vendor.id, "payable_amount": str(amount), "source": "vendor_association"})
        return payable

    async def remove_auto_from_association(self, project_id: int, vendor_id: int) -> bool:
        """指派刪除時，自動建且未付的應付一併撤；人工建的或已付的保留（會在 weekly 99 家族被看到）。"""
        return (await self.ensure_from_association(project_id, vendor_id, 0)) is None

    async def delete(self, payable_id: int) -> bool:
        """刪除廠商應付 — 同步清理對應帳本 entries"""
        await self.ledger_service.delete_by_source("erp_vendor_payable", payable_id)
        result = await self.repo.delete(payable_id)
        if result:
            await self.audit_delete(payable_id)
        return result
