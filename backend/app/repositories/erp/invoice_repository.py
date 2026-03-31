"""ERP 發票 Repository"""
import logging
from typing import Optional, List, Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPInvoice
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ERPInvoiceRepository(BaseRepository[ERPInvoice]):
    """發票資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ERPInvoice)

    async def get_by_quotation_id(self, quotation_id: int) -> List[ERPInvoice]:
        """取得報價單所有發票"""
        query = (
            select(ERPInvoice)
            .where(ERPInvoice.erp_quotation_id == quotation_id)
            .order_by(ERPInvoice.invoice_date.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_invoice_number(self, invoice_number: str) -> Optional[ERPInvoice]:
        """依發票號碼查詢"""
        return await self.find_one_by(invoice_number=invoice_number)

    async def get_invoice_summary(
        self, invoice_type: Optional[str] = None, year: Optional[int] = None,
        skip: int = 0, limit: int = 50,
    ) -> tuple:
        """跨案件發票彙總 — 銷項/進項分類查詢"""
        from app.extended.models.erp import ERPQuotation

        query = (
            select(
                ERPInvoice,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
                ERPQuotation.project_code,
            )
            .join(ERPQuotation, ERPInvoice.erp_quotation_id == ERPQuotation.id)
        )

        if invoice_type:
            query = query.where(ERPInvoice.invoice_type == invoice_type)
        if year:
            query = query.where(ERPQuotation.year == year)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Results
        query = query.order_by(ERPInvoice.invoice_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        rows = result.all()

        items = []
        for inv, case_code, case_name, project_code in rows:
            items.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
                "amount": str(inv.amount),
                "tax_amount": str(inv.tax_amount or 0),
                "invoice_type": inv.invoice_type,
                "status": inv.status,
                "description": inv.description,
                "case_code": case_code,
                "project_code": project_code,
                "case_name": case_name,
                "billing_id": inv.billing_id,
                "erp_quotation_id": inv.erp_quotation_id,
            })

        return items, total

    async def get_counts_by_quotation_ids(
        self, quotation_ids: List[int]
    ) -> Dict[int, int]:
        """批次取得各報價單的發票數量"""
        if not quotation_ids:
            return {}
        query = (
            select(
                ERPInvoice.erp_quotation_id,
                func.count(ERPInvoice.id).label("cnt"),
            )
            .where(ERPInvoice.erp_quotation_id.in_(quotation_ids))
            .group_by(ERPInvoice.erp_quotation_id)
        )
        result = await self.db.execute(query)
        return {row.erp_quotation_id: row.cnt for row in result.all()}
