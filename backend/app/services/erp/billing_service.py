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
        """建立請款 (ADR-0013 Phase 2: 自動生成 billing_code)"""
        dump = data.model_dump()

        # 自動生成 billing_code (若呼叫端未提供)
        if not dump.get("billing_code"):
            from datetime import datetime
            from app.services.case_code_service import CaseCodeService
            code_svc = CaseCodeService(self.db)
            dump["billing_code"] = await code_svc.generate_billing_code(
                year=datetime.now().year
            )

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

        # v2.0.0: 收款確認 → 同步帳本入帳 (冪等：已有 entry 則跳過)
        new_status = billing.payment_status
        if new_status == "paid" and old_status != "paid" and billing.payment_amount:
            existing = await self.ledger_service.find_by_source("erp_billing", billing.id)
            if existing:
                logger.warning("帳本已有 erp_billing/%d 的 entry，跳過重複入帳", billing.id)
            else:
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

        await self.db.commit()
        await self.audit_update(billing_id, update_data)

        # EventBus 通知 (非關鍵路徑 — 用於通知推播，失敗不影響帳本)
        if new_status == "paid" and old_status != "paid":
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
