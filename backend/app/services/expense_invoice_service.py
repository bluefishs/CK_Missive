from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException
from typing import Optional, List, Tuple
from decimal import Decimal

from app.extended.models.invoice import ExpenseInvoice, ExpenseInvoiceItem
from app.extended.models.finance import FinanceLedger
from app.schemas.erp.expense import ExpenseInvoiceCreate, ExpenseInvoiceUpdate, ExpenseInvoiceQuery
from app.repositories.erp.expense_invoice_repository import ExpenseInvoiceRepository
from app.services.finance_ledger_service import FinanceLedgerService

class ExpenseInvoiceService:
    """費用報銷發票業務服務層"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExpenseInvoiceRepository(db)
        self.ledger_service = FinanceLedgerService(db)

    async def create(self, data: ExpenseInvoiceCreate, user_id: Optional[int] = None) -> ExpenseInvoice:
        """建立報銷發票 (含重複檢查)，狀態為 pending 待審核

        帳本記錄在 approve() 審核通過時才寫入，避免雙重記帳。
        """
        # 1. 檢查是否有重複發票
        is_duplicate = await self.repo.check_duplicate(data.inv_num)
        if is_duplicate:
            raise ValueError(f"發票號碼 {data.inv_num} 已存在，請確認是否重複報銷。")

        # 2. 建立 ExpenseInvoice 主檔 (status=pending，等待審核)
        invoice = ExpenseInvoice(
            inv_num=data.inv_num,
            date=data.date,
            amount=data.amount,
            tax_amount=data.tax_amount,
            buyer_ban=data.buyer_ban,
            seller_ban=data.seller_ban,
            case_code=data.case_code,
            category=data.category,
            source=data.source,
            notes=data.notes,
            user_id=user_id,
            status="pending"
        )
        self.db.add(invoice)
        await self.db.flush()  # 先推進以取得 ID

        # 3. 建立 Items
        if data.items:
            for item_in in data.items:
                item = ExpenseInvoiceItem(
                    invoice_id=invoice.id,
                    item_name=item_in.item_name,
                    qty=item_in.qty,
                    unit_price=item_in.unit_price,
                    amount=item_in.amount
                )
                self.db.add(item)

        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def get_by_id(self, invoice_id: int) -> Optional[ExpenseInvoice]:
        """取得發票詳情"""
        return await self.repo.get_by_id(invoice_id)

    async def update(self, invoice_id: int, data: "ExpenseInvoiceUpdate") -> Optional[ExpenseInvoice]:
        """更新發票部分欄位"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        update_data = data.model_dump(exclude_unset=True) if hasattr(data, 'model_dump') else data
        for key, value in update_data.items():
            if value is not None:
                setattr(invoice, key, value)
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def approve(self, invoice_id: int) -> Optional[ExpenseInvoice]:
        """審核通過 — 自動寫入帳本"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        if invoice.status == "verified":
            raise ValueError("此發票已審核通過，不可重複審核")
        if invoice.status == "rejected":
            raise ValueError("此發票已被駁回，不可審核")

        invoice.status = "verified"

        # 自動建立帳本記錄
        ledger = FinanceLedger(
            amount=invoice.amount,
            entry_type="expense",
            category=invoice.category or "報銷及費用",
            description=f"發票報銷 (號碼: {invoice.inv_num})",
            case_code=invoice.case_code,
            user_id=invoice.user_id,
            source_type="expense_invoice",
            source_id=invoice.id,
            transaction_date=invoice.date,
        )
        self.db.add(ledger)
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def reject(self, invoice_id: int, reason: Optional[str] = None) -> Optional[ExpenseInvoice]:
        """駁回報銷"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        if invoice.status == "verified":
            raise ValueError("此發票已審核通過，不可駁回")

        invoice.status = "rejected"
        if reason:
            invoice.notes = f"[駁回] {reason}" if not invoice.notes else f"{invoice.notes}\n[駁回] {reason}"
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    def parse_qr_data(self, raw_qr: str) -> dict:
        """解析台灣電子發票 QR Code 資料

        QR 格式 (前 77 字元):
        - [0:10]  發票號碼 (2 英文 + 8 數字)
        - [10:17] 民國日期 (YYYMMDD)
        - [17:25] 隨機碼
        - [25:33] 買方統編 (8 碼)
        - [33:41] 賣方統編 (8 碼)
        - [41:49] 金額 hex (8 碼, 16 進位)
        """
        if len(raw_qr) < 49:
            raise ValueError("QR 資料格式不正確，長度不足")

        inv_num = raw_qr[0:10]
        date_str = raw_qr[10:17]  # 民國年 YYYMMDD
        buyer_ban = raw_qr[25:33]
        seller_ban = raw_qr[33:41]
        amount_hex = raw_qr[41:49]

        # 民國年轉西元
        from datetime import date as date_type
        roc_year = int(date_str[0:3])
        month = int(date_str[3:5])
        day = int(date_str[5:7])
        inv_date = date_type(roc_year + 1911, month, day)

        # 金額 hex → Decimal
        amount = Decimal(str(int(amount_hex, 16)))

        return {
            "inv_num": inv_num,
            "date": inv_date,
            "buyer_ban": buyer_ban,
            "seller_ban": seller_ban,
            "amount": amount,
            "source": "qr_scan",
            "raw_qr_data": raw_qr,
        }

    async def create_from_qr(
        self, raw_qr: str, case_code: Optional[str] = None,
        category: Optional[str] = None, user_id: Optional[int] = None,
    ) -> ExpenseInvoice:
        """從 QR Code 建立報銷發票"""
        parsed = self.parse_qr_data(raw_qr)

        data = ExpenseInvoiceCreate(
            inv_num=parsed["inv_num"],
            date=parsed["date"],
            amount=parsed["amount"],
            buyer_ban=parsed["buyer_ban"],
            seller_ban=parsed["seller_ban"],
            case_code=case_code,
            category=category,
            source="qr_scan",
        )
        return await self.create(data, user_id=user_id)

    async def list_by_case(self, case_code: str, skip=0, limit=20) -> Tuple[List[ExpenseInvoice], int]:
        return await self.repo.find_by_case_code(case_code, skip, limit)

    async def query(self, params: ExpenseInvoiceQuery) -> Tuple[List[ExpenseInvoice], int]:
        return await self.repo.query(params)
