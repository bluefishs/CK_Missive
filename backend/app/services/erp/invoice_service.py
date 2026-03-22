"""ERP 發票服務

Version: 1.1.0
- v1.1.0: CRUD 改用 Repository 方法 (合規修正)
"""
import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.erp import ERPInvoiceRepository
from app.schemas.erp import ERPInvoiceCreate, ERPInvoiceUpdate, ERPInvoiceResponse

logger = logging.getLogger(__name__)


class ERPInvoiceService:
    """發票管理服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ERPInvoiceRepository(db)

    async def create(self, data: ERPInvoiceCreate) -> ERPInvoiceResponse:
        """建立發票"""
        invoice = await self.repo.create(data.model_dump())
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
        return ERPInvoiceResponse.model_validate(invoice)

    async def delete(self, invoice_id: int) -> bool:
        """刪除發票"""
        return await self.repo.delete(invoice_id)
