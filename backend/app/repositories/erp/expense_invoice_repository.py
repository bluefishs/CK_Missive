from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base_repository import BaseRepository
from app.extended.models.invoice import ExpenseInvoice, ExpenseInvoiceItem
from app.schemas.erp.expense import ExpenseInvoiceQuery

class ExpenseInvoiceRepository(BaseRepository[ExpenseInvoice]):
    """費用報銷發票 Repository，支援 AsyncSession"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, ExpenseInvoice)

    async def find_by_inv_num(self, inv_num: str) -> Optional[ExpenseInvoice]:
        query = select(self.model).where(self.model.inv_num == inv_num)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def check_duplicate(self, inv_num: str) -> bool:
        exists = await self.find_by_inv_num(inv_num)
        return exists is not None

    async def find_by_case_code(self, case_code: str, skip=0, limit=20) -> Tuple[List[ExpenseInvoice], int]:
        base_query = select(self.model).where(self.model.case_code == case_code)
        
        # 取得總數
        count_query = select(func.count()).select_from(base_query.subquery())
        total = await self.db.scalar(count_query)
        
        # 取得列表
        data_query = base_query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(data_query)
        items = result.scalars().all()
        
        return list(items), total or 0

    async def query(self, params: ExpenseInvoiceQuery) -> Tuple[List[ExpenseInvoice], int]:
        stmt = select(self.model)
        
        if params.case_code:
            stmt = stmt.where(self.model.case_code == params.case_code)
        if params.category:
            stmt = stmt.where(self.model.category == params.category)
        if params.status:
            stmt = stmt.where(self.model.status == params.status)
        if params.user_id:
            stmt = stmt.where(self.model.user_id == params.user_id)
        if params.date_from:
            stmt = stmt.where(self.model.date >= params.date_from)
        if params.date_to:
            stmt = stmt.where(self.model.date <= params.date_to)

        count_query = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_query)

        stmt = stmt.order_by(self.model.created_at.desc()).offset(params.skip).limit(params.limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        return list(items), total or 0

    async def create_with_items(
        self, invoice: ExpenseInvoice, items: List[ExpenseInvoiceItem]
    ) -> ExpenseInvoice:
        """新增發票主檔 + 明細項目，flush 取 ID 後逐一加入 items"""
        self.db.add(invoice)
        await self.db.flush()

        for item in items:
            item.invoice_id = invoice.id
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def update_fields(self, invoice: ExpenseInvoice, data: dict) -> ExpenseInvoice:
        """逐一更新指定欄位"""
        for key, value in data.items():
            if value is not None:
                setattr(invoice, key, value)
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def update_status(
        self, invoice: ExpenseInvoice, status: str, notes_append: Optional[str] = None
    ) -> ExpenseInvoice:
        """更新狀態，可選追加備註"""
        invoice.status = status
        if notes_append:
            invoice.notes = (
                f"{invoice.notes}\n{notes_append}" if invoice.notes else notes_append
            )
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def commit(self):
        """委派 session commit"""
        await self.db.commit()
