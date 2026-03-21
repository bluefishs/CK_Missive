from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple
from datetime import date
from decimal import Decimal

from app.extended.models.finance import FinanceLedger
from app.extended.models.invoice import ExpenseInvoice
from app.schemas.erp.ledger import LedgerCreate, LedgerQuery
from app.repositories.erp.ledger_repository import LedgerRepository

class FinanceLedgerService:
    """統一帳本業務服務層"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LedgerRepository(db)

    async def record(self, data: LedgerCreate, user_id: Optional[int] = None) -> FinanceLedger:
        """手動建立一筆帳目"""
        ledger = FinanceLedger(
            amount=data.amount,
            entry_type=data.entry_type,
            category=data.category,
            description=data.description,
            case_code=data.case_code,
            user_id=user_id,
            source_type="manual",
            transaction_date=data.transaction_date or date.today()
        )
        self.db.add(ledger)
        await self.db.commit()
        await self.db.refresh(ledger)
        return ledger

    async def record_from_expense(self, invoice: ExpenseInvoice) -> FinanceLedger:
        """從報銷發票自動產生帳本記錄"""
        ledger = FinanceLedger(
            amount=invoice.amount,
            entry_type="expense",
            category=invoice.category or "報銷及費用",
            description=f"發票報銷 (號碼: {invoice.inv_num})",
            case_code=invoice.case_code,
            user_id=invoice.user_id,
            source_type="expense_invoice",
            source_id=invoice.id,
            transaction_date=invoice.date
        )
        self.db.add(ledger)
        # Service 負責 commit 回傳
        await self.db.commit()
        await self.db.refresh(ledger)
        return ledger

    async def create(self, data: LedgerCreate, user_id: Optional[int] = None) -> FinanceLedger:
        """手動建立帳目 (別名，與 record 等價)"""
        return await self.record(data, user_id=user_id)

    async def get_by_id(self, ledger_id: int) -> Optional[FinanceLedger]:
        """取得帳本記錄"""
        return await self.repo.get_by_id(ledger_id)

    async def delete(self, ledger_id: int) -> bool:
        """刪除帳本記錄 (僅限手動記帳)"""
        ledger = await self.repo.get_by_id(ledger_id)
        if not ledger:
            return False
        if ledger.source_type != "manual":
            raise ValueError("僅可刪除手動記帳的記錄，系統自動入帳請從原始單據處理")
        await self.db.delete(ledger)
        await self.db.flush()
        await self.db.commit()
        return True

    async def get_case_balance(self, case_code: str) -> dict:
        """查詢特定專案收支餘額"""
        return await self.repo.get_case_balance(case_code)

    async def get_category_breakdown(
        self, case_code: Optional[str] = None,
        date_from=None, date_to=None, entry_type: Optional[str] = None,
    ) -> list:
        """帳本分類拆解 (SQL GROUP BY)"""
        return await self.repo.get_category_breakdown(
            case_code=case_code,
            date_from=date_from,
            date_to=date_to,
            entry_type=entry_type,
        )

    async def get_balance(self, case_code: Optional[str] = None) -> dict:
        """查詢餘額"""
        if case_code:
            return await self.repo.get_case_balance(case_code)
        # TODO: 全公司餘額邏輯
        return {"income": 0, "expense": 0, "net": 0}

    async def query(self, params: LedgerQuery) -> Tuple[List[FinanceLedger], int]:
        """多條件查詢與分頁"""
        return await self.repo.query(params)
