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
