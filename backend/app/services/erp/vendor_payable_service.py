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
from app.services.finance_ledger_service import FinanceLedgerService
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
        """建立廠商應付 — 自動由 vendor_code 配對 vendor_id"""
        create_data = data.model_dump()
        # 自動配對 vendor_id
        if not create_data.get("vendor_id") and create_data.get("vendor_code"):
            create_data["vendor_id"] = await self._resolve_vendor_id(
                vendor_code=create_data["vendor_code"]
            )
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

        await self.db.flush()
        await self.db.refresh(payable)

        # AP 自動拋轉：非 paid → paid 且有付款金額時入帳
        new_status = payable.payment_status
        if old_status != "paid" and new_status == "paid" and payable.paid_amount:
            case_code = await self._get_case_code(payable.erp_quotation_id)
            if case_code:
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

    async def _resolve_vendor_id(self, vendor_code: Optional[str] = None) -> Optional[int]:
        """由 vendor_code 查找 partner_vendors.id"""
        if not vendor_code:
            return None
        vendor = await self._vendor_repo.find_one_by(vendor_code=vendor_code)
        return vendor.id if vendor else None

    async def delete(self, payable_id: int) -> bool:
        """刪除廠商應付"""
        result = await self.repo.delete(payable_id)
        if result:
            await self.audit_delete(payable_id)
        return result
