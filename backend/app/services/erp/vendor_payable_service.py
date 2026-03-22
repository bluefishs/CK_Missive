"""ERP 廠商應付服務

Version: 1.2.0
- v1.2.0: create/delete 改用 Repository 方法 (合規修正)
- v1.1.0: 付款確認時自動寫入 FinanceLedger (AP 自動拋轉)
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.extended.models.erp import ERPVendorPayable, ERPQuotation
from app.repositories.erp import ERPVendorPayableRepository
from app.schemas.erp import ERPVendorPayableCreate, ERPVendorPayableUpdate, ERPVendorPayableResponse
from app.services.finance_ledger_service import FinanceLedgerService

logger = logging.getLogger(__name__)


class ERPVendorPayableService:
    """廠商應付管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPVendorPayableRepository(db)
        self.ledger_service = FinanceLedgerService(db)

    async def create(self, data: ERPVendorPayableCreate) -> ERPVendorPayableResponse:
        """建立廠商應付"""
        payable = await self.repo.create(data.model_dump())
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
                )
                logger.info(
                    f"AP 自動入帳: 廠商 {payable.vendor_name}, "
                    f"金額 {payable.paid_amount}, 案號 {case_code}"
                )

        await self.db.commit()
        return ERPVendorPayableResponse.model_validate(payable)

    async def _get_case_code(self, quotation_id: int) -> Optional[str]:
        """透過報價單取得案號"""
        stmt = select(ERPQuotation.case_code).where(ERPQuotation.id == quotation_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, payable_id: int) -> bool:
        """刪除廠商應付"""
        return await self.repo.delete(payable_id)
