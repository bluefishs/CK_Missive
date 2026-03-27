from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base_repository import BaseRepository
from app.extended.models.finance import FinanceLedger
from app.schemas.erp.ledger import LedgerQuery

class LedgerRepository(BaseRepository[FinanceLedger]):
    """統一帳本 Repository，支援 AsyncSession"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, FinanceLedger)

    async def get_case_balance(self, case_code: str) -> dict:
        """某專案收支餘額 {income, expense, net}"""
        stmt = select(
            self.model.entry_type,
            func.sum(self.model.amount).label("total")
        ).where(self.model.case_code == case_code).group_by(self.model.entry_type)
        
        result = await self.db.execute(stmt)
        records = result.all()
        
        from decimal import Decimal
        balance = {"income": Decimal("0"), "expense": Decimal("0"), "net": Decimal("0")}
        for row in records:
            _type, _total = row.entry_type, row.total
            if _type == "income":
                balance["income"] = _total or Decimal("0")
            elif _type == "expense":
                balance["expense"] = _total or Decimal("0")

        balance["net"] = balance["income"] - balance["expense"]
        return balance

    async def get_company_balance(self) -> dict:
        """全公司收支餘額 {income, expense, net}"""
        from decimal import Decimal

        stmt = select(
            self.model.entry_type,
            func.sum(self.model.amount).label("total")
        ).group_by(self.model.entry_type)

        result = await self.db.execute(stmt)
        records = result.all()

        balance = {"income": Decimal("0"), "expense": Decimal("0"), "net": Decimal("0")}
        for row in records:
            _type, _total = row.entry_type, row.total
            if _type == "income":
                balance["income"] = _total or Decimal("0")
            elif _type == "expense":
                balance["expense"] = _total or Decimal("0")

        balance["net"] = balance["income"] - balance["expense"]
        return balance

    async def query(self, params: LedgerQuery) -> Tuple[List[FinanceLedger], int]:
        stmt = select(self.model)
        
        if params.case_code:
            stmt = stmt.where(self.model.case_code == params.case_code)
        if params.entry_type:
            stmt = stmt.where(self.model.entry_type == params.entry_type)
        if params.category:
            stmt = stmt.where(self.model.category == params.category)
        if params.user_id:
            stmt = stmt.where(self.model.user_id == params.user_id)
        if params.date_from:
            stmt = stmt.where(self.model.transaction_date >= params.date_from)
        if params.date_to:
            stmt = stmt.where(self.model.transaction_date <= params.date_to)

        count_query = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_query)

        stmt = stmt.order_by(self.model.transaction_date.desc()).offset(params.skip).limit(params.limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        return list(items), total or 0

    async def get_category_breakdown(
        self,
        case_code: Optional[str] = None,
        date_from=None,
        date_to=None,
        entry_type: Optional[str] = None,
    ) -> list:
        """按 category 分組統計 (SQL GROUP BY)"""
        from decimal import Decimal

        stmt = select(
            self.model.category,
            func.sum(self.model.amount).label("total"),
            func.count().label("count"),
        )

        if case_code:
            stmt = stmt.where(self.model.case_code == case_code)
        if entry_type:
            stmt = stmt.where(self.model.entry_type == entry_type)
        if date_from:
            stmt = stmt.where(self.model.transaction_date >= date_from)
        if date_to:
            stmt = stmt.where(self.model.transaction_date <= date_to)

        stmt = stmt.group_by(self.model.category).order_by(func.sum(self.model.amount).desc())
        result = await self.db.execute(stmt)

        return [
            {
                "category": row.category or "未分類",
                "total": row.total or Decimal("0"),
                "count": row.count,
            }
            for row in result.all()
        ]

    async def create_entry(self, ledger: FinanceLedger) -> FinanceLedger:
        """新增帳本記錄 (flush only — 由呼叫端控制 commit 以確保交易原子性)"""
        self.db.add(ledger)
        await self.db.flush()
        await self.db.refresh(ledger)
        return ledger

    async def delete_entry(self, ledger: FinanceLedger) -> bool:
        """刪除帳本記錄"""
        await self.db.delete(ledger)
        await self.db.flush()
        await self.db.commit()
        return True
