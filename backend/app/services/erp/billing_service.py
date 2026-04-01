"""ERP 請款服務

Version: 1.2.0
- v1.2.0: create/delete 改用 Repository 方法 (合規修正)
- v1.1.0: Phase 5-6 收款確認自動寫入 Ledger
"""
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPBilling
from app.repositories.erp import ERPBillingRepository, ERPQuotationRepository
from app.schemas.erp import ERPBillingCreate, ERPBillingUpdate, ERPBillingResponse
from app.services.finance_ledger_service import FinanceLedgerService
from app.services.audit_mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class ERPBillingService(AuditableServiceMixin):
    """請款管理服務"""

    AUDIT_TABLE = "erp_billings"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPBillingRepository(db)
        self._quotation_repo = ERPQuotationRepository(db)
        self.ledger_service = FinanceLedgerService(db)

    async def create(self, data: ERPBillingCreate) -> ERPBillingResponse:
        """建立請款"""
        dump = data.model_dump()
        billing = await self.repo.create(dump)
        await self.audit_create(billing.id, dump)
        return ERPBillingResponse.model_validate(billing)

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

        await self.db.flush()
        await self.db.refresh(billing)

        # Phase 5-6: 收款確認 → 自動寫入 Ledger + 系統通知
        new_status = billing.payment_status
        if new_status == "paid" and old_status != "paid" and billing.payment_amount:
            case_code = await self._get_case_code(billing.erp_quotation_id)
            await self.ledger_service.record_from_billing(
                billing_id=billing.id,
                case_code=case_code,
                payment_amount=billing.payment_amount,
                payment_date=billing.payment_date,
                billing_period=billing.billing_period,
            )
            # 收款確認通知
            try:
                from app.services.notification_service import NotificationService
                period_text = f" ({billing.billing_period})" if billing.billing_period else ""
                await NotificationService.create_notification(
                    db=self.db,
                    notification_type="erp_payment",
                    severity="info",
                    title=f"收款確認 — {case_code}",
                    message=f"{case_code}{period_text} 收款 ${billing.payment_amount:,.0f} 已入帳",
                    source_table="erp_billings",
                    source_id=billing.id,
                )
            except Exception as e:
                logger.warning(f"收款通知發送失敗 (不影響收款): {e}")

        await self.db.commit()
        await self.audit_update(billing_id, update_data)
        return ERPBillingResponse.model_validate(billing)

    async def delete(self, billing_id: int) -> bool:
        """刪除請款"""
        result = await self.repo.delete(billing_id)
        if result:
            await self.audit_delete(billing_id)
        return result

    async def _get_case_code(self, quotation_id: int) -> str:
        """從報價單取得 case_code"""
        quotation = await self._quotation_repo.get_by_id(quotation_id)
        return quotation.case_code if quotation and quotation.case_code else "一般營運"
