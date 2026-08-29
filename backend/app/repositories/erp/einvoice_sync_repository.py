import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.einvoice_sync import EInvoiceSyncLog
from app.extended.models.invoice import ExpenseInvoice, ExpenseInvoiceItem

logger = logging.getLogger(__name__)


class EInvoiceSyncRepository:
    """電子發票同步 Repository — 管理 EInvoiceSyncLog + ExpenseInvoice 同步操作"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- ExpenseInvoice 查詢/寫入 --

    async def get_existing_inv_nums(self, inv_nums: list[str]) -> set[str]:
        if not inv_nums:
            return set()
        result = await self.db.execute(
            select(ExpenseInvoice.inv_num).where(
                ExpenseInvoice.inv_num.in_(inv_nums)
            )
        )
        return {row[0] for row in result.fetchall()}

    async def create_invoice(self, invoice: ExpenseInvoice) -> ExpenseInvoice:
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    async def add_invoice_item(self, item: ExpenseInvoiceItem):
        self.db.add(item)

    async def get_invoice_by_id(self, invoice_id: int) -> Optional[ExpenseInvoice]:
        return await self.db.get(ExpenseInvoice, invoice_id)

    async def get_pending_receipts(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[list[ExpenseInvoice], int, object]:
        count_q = (
            select(func.count())
            .select_from(ExpenseInvoice)
            .where(ExpenseInvoice.status == "pending_receipt")
        )
        total = (await self.db.execute(count_q)).scalar() or 0

        # 2026-08-29（development-rules §2.6 ①）：統計卡的數字要**分頁前的全量**。
        # 前端「待核銷金額」原本是 `pendingItems.reduce(...)` ＝ 只加當頁，
        # 而同一排的「待核銷發票」用的是這裡的 total ⇒ **同一排卡片一個當頁
        # 一個全量**，筆數與金額對不起來而畫面上看不出來。
        # 用同一個 where 條件（不另寫一份篩選，免得兩個數字各自演化）。
        amount_q = (
            select(func.coalesce(func.sum(ExpenseInvoice.amount), 0))
            .where(ExpenseInvoice.status == "pending_receipt")
        )
        total_amount = (await self.db.execute(amount_q)).scalar() or 0

        query = (
            select(ExpenseInvoice)
            .where(ExpenseInvoice.status == "pending_receipt")
            .order_by(ExpenseInvoice.date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total, total_amount

    async def update_invoice_receipt(
        self,
        invoice: ExpenseInvoice,
        receipt_path: str,
        case_code: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> ExpenseInvoice:
        invoice.receipt_image_path = receipt_path
        invoice.status = "pending"
        invoice.user_id = user_id
        if case_code is not None:
            invoice.case_code = case_code
        if category is not None:
            invoice.category = category
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    # -- EInvoiceSyncLog CRUD --

    async def create_sync_log(self, sync_log: EInvoiceSyncLog) -> EInvoiceSyncLog:
        self.db.add(sync_log)
        await self.db.flush()
        return sync_log

    async def update_sync_log(self, sync_log: EInvoiceSyncLog):
        await self.db.flush()

    async def get_sync_logs(
        self, skip: int = 0, limit: int = 10
    ) -> tuple[list[EInvoiceSyncLog], int]:
        count_q = select(func.count()).select_from(EInvoiceSyncLog)
        total = (await self.db.execute(count_q)).scalar() or 0

        # 2026-08-29（development-rules §2.6 ①）：統計卡的數字要**分頁前的全量**。
        # 前端「待核銷金額」原本是 `pendingItems.reduce(...)` ＝ 只加當頁，
        # 而同一排的「待核銷發票」用的是這裡的 total ⇒ **同一排卡片一個當頁
        # 一個全量**，筆數與金額對不起來而畫面上看不出來。
        # 用同一個 where 條件（不另寫一份篩選，免得兩個數字各自演化）。
        amount_q = (
            select(func.coalesce(func.sum(ExpenseInvoice.amount), 0))
            .where(ExpenseInvoice.status == "pending_receipt")
        )
        total_amount = (await self.db.execute(amount_q)).scalar() or 0

        query = (
            select(EInvoiceSyncLog)
            .order_by(EInvoiceSyncLog.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total, total_amount

    # -- 事務控制 --

    async def commit(self):
        await self.db.commit()
