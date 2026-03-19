"""ERP 發票 Repository"""
import logging
from typing import Optional, List

from sqlalchemy import select
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
