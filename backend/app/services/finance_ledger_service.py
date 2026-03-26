from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple
from datetime import date

from app.extended.models.finance import FinanceLedger
from app.extended.models.invoice import ExpenseInvoice
from app.schemas.erp.ledger import LedgerCreate, LedgerQuery
from app.repositories.erp.ledger_repository import LedgerRepository
from app.services.audit_mixin import AuditableServiceMixin

class FinanceLedgerService(AuditableServiceMixin):
    """統一帳本業務服務層"""

    AUDIT_TABLE = "finance_ledgers"

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
        result = await self.repo.create_entry(ledger)
        await self.audit_create(result.id, data.model_dump(), user_id=user_id)
        return result

    async def record_from_expense(self, invoice: ExpenseInvoice) -> FinanceLedger:
        """從報銷發票自動產生帳本記錄 (amount 已是 TWD 本位幣)"""
        desc = f"發票報銷 (號碼: {invoice.inv_num})"
        if invoice.currency and invoice.currency != "TWD":
            desc += f" [{invoice.currency} {invoice.original_amount} × {invoice.exchange_rate}]"
        ledger = FinanceLedger(
            amount=invoice.amount,
            entry_type="expense",
            category=invoice.category or "報銷及費用",
            description=desc,
            case_code=invoice.case_code,
            user_id=invoice.user_id,
            source_type="expense_invoice",
            source_id=invoice.id,
            transaction_date=invoice.date,
            vendor_id=getattr(invoice, "vendor_id", None),
        )
        return await self.repo.create_entry(ledger)

    async def record_from_billing(
        self, billing_id: int, case_code: str,
        payment_amount, payment_date=None,
        billing_period: Optional[str] = None,
    ) -> FinanceLedger:
        """從請款收款確認自動產生帳本收入記錄"""
        from decimal import Decimal
        amount = Decimal(str(payment_amount)) if not isinstance(payment_amount, Decimal) else payment_amount
        desc = f"請款收款 (請款 #{billing_id})"
        if billing_period:
            desc += f" [{billing_period}]"
        ledger = FinanceLedger(
            amount=amount,
            entry_type="income",
            category="收款",
            description=desc,
            case_code=case_code,
            source_type="erp_billing",
            source_id=billing_id,
            transaction_date=payment_date or date.today(),
        )
        return await self.repo.create_entry(ledger)

    async def record_from_vendor_payable(
        self, payable_id: int, case_code: str,
        paid_amount, paid_date=None,
        vendor_name: Optional[str] = None,
        description: Optional[str] = None,
        vendor_id: Optional[int] = None,
    ) -> FinanceLedger:
        """從廠商應付付款確認自動產生帳本支出記錄"""
        from decimal import Decimal
        amount = Decimal(str(paid_amount)) if not isinstance(paid_amount, Decimal) else paid_amount
        desc = f"廠商付款 (應付 #{payable_id})"
        if vendor_name:
            desc += f" [{vendor_name}]"
        if description:
            desc += f" {description}"
        ledger = FinanceLedger(
            amount=amount,
            entry_type="expense",
            category="外包及勞務",
            description=desc,
            case_code=case_code,
            source_type="erp_vendor_payable",
            source_id=payable_id,
            transaction_date=paid_date or date.today(),
            vendor_id=vendor_id,
        )
        return await self.repo.create_entry(ledger)

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
        result = await self.repo.delete_entry(ledger)
        if result:
            await self.audit_delete(ledger_id)
        return result

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
