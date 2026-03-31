"""ERP 發票服務

Version: 1.2.0
- v1.2.0: 新增 create_from_billing — 從請款記錄開立發票
- v1.1.0: CRUD 改用 Repository 方法 (合規修正)
"""
import logging
from typing import Optional, List
from datetime import datetime, date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.erp import ERPInvoiceRepository
from app.schemas.erp import ERPInvoiceCreate, ERPInvoiceUpdate, ERPInvoiceResponse
from app.services.audit_mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class ERPInvoiceService(AuditableServiceMixin):
    """發票管理服務"""

    AUDIT_TABLE = "erp_invoices"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPInvoiceRepository(db)

    async def create(self, data: ERPInvoiceCreate) -> ERPInvoiceResponse:
        """建立發票"""
        dump = data.model_dump()
        invoice = await self.repo.create(dump)
        await self.audit_create(invoice.id, dump)
        return ERPInvoiceResponse.model_validate(invoice)

    async def get_by_quotation(self, quotation_id: int) -> List[ERPInvoiceResponse]:
        """取得報價單所有發票"""
        items = await self.repo.get_by_quotation_id(quotation_id)
        return [ERPInvoiceResponse.model_validate(i) for i in items]

    async def update(self, invoice_id: int, data: ERPInvoiceUpdate) -> Optional[ERPInvoiceResponse]:
        """更新發票"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 作廢處理
        if update_data.get("status") == "voided" and invoice.status != "voided":
            update_data["voided_at"] = datetime.utcnow()

        invoice = await self.repo.update(invoice_id, update_data)
        await self.audit_update(invoice_id, update_data)
        return ERPInvoiceResponse.model_validate(invoice)

    async def get_invoice_summary(
        self,
        invoice_type: Optional[str] = None,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """跨案件發票彙總"""
        items, total = await self.repo.get_invoice_summary(
            invoice_type=invoice_type, year=year, skip=skip, limit=limit,
        )
        return {"items": items, "total": total}

    async def delete(self, invoice_id: int) -> bool:
        """刪除發票"""
        result = await self.repo.delete(invoice_id)
        if result:
            await self.audit_delete(invoice_id)
        return result

    async def create_from_billing(
        self,
        billing_id: int,
        invoice_number: str,
        invoice_date: Optional[date_type] = None,
        notes: Optional[str] = None,
    ) -> ERPInvoiceResponse:
        """從請款記錄建立銷項發票"""
        from app.extended.models.erp import ERPBilling

        result = await self.db.execute(
            select(ERPBilling).where(ERPBilling.id == billing_id)
        )
        billing = result.scalars().first()
        if not billing:
            raise ValueError("請款記錄不存在")

        if billing.invoice_id:
            raise ValueError("此請款記錄已有關聯發票")

        invoice_data = {
            "erp_quotation_id": billing.erp_quotation_id,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date or date_type.today(),
            "amount": billing.billing_amount,
            "tax_amount": 0,
            "invoice_type": "sales",
            "description": f"請款期別: {billing.billing_period or '-'}",
            "status": "issued",
            "billing_id": billing_id,
            "notes": notes,
        }

        invoice = await self.repo.create(invoice_data)
        await self.audit_create(invoice.id, invoice_data)

        # 雙向關聯: billing.invoice_id → invoice
        billing.invoice_id = invoice.id
        await self.db.commit()
        await self.db.refresh(invoice)

        return ERPInvoiceResponse.model_validate(invoice)
