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
from app.services.audit_mixin import AuditableServiceMixin

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
        payable = await self.repo.create(create_data)
        await self.audit_create(payable.id, create_data)
        return ERPVendorPayableResponse.model_validate(payable)

    async def get_by_quotation(self, quotation_id: int) -> List[ERPVendorPayableResponse]:
        """取得報價單所有應付"""
        items = await self.repo.get_by_quotation_id(quotation_id)
        return [ERPVendorPayableResponse.model_validate(p) for p in items]

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

        await self.db.flush()
        await self.db.refresh(payable)

        # AP 自動拋轉：非 paid → paid 且有付款金額時入帳 (冪等)
        new_status = payable.payment_status
        if old_status != "paid" and new_status == "paid" and payable.paid_amount:
            existing = await self.ledger_service.find_by_source("erp_vendor_payable", payable.id)
            if existing:
                logger.warning("帳本已有 erp_vendor_payable/%d 的 entry，跳過重複入帳", payable.id)
            elif (case_code := await self._get_case_code(payable.erp_quotation_id)):
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
                    f"AP 自動入帳: 廠商 {payable.vendor_name}, "
                    f"金額 {payable.paid_amount}, 案號 {case_code}"
                )

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

    async def delete(self, payable_id: int) -> bool:
        """刪除廠商應付 — 同步清理對應帳本 entries"""
        await self.ledger_service.delete_by_source("erp_vendor_payable", payable_id)
        result = await self.repo.delete(payable_id)
        if result:
            await self.audit_delete(payable_id)
        return result
