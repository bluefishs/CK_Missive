from typing import Optional, List, Tuple
from datetime import date
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

    def _apply_query_filters(self, stmt, params: LedgerQuery):
        """list 與 totals 共用同一組濾鏡 —— 各寫一份遲早漂移（跨檔 SSOT 家族）"""
        if params.case_code:
            stmt = stmt.where(self.model.case_code == params.case_code)
        if params.entry_type:
            stmt = stmt.where(self.model.entry_type == params.entry_type)
        if params.category:
            stmt = stmt.where(self.model.category == params.category)
        if params.user_id:
            # rls-noqa: 同 expense_invoice：可選篩選條件而非強制 RLS
            stmt = stmt.where(self.model.user_id == params.user_id)
        if params.date_from:
            stmt = stmt.where(self.model.transaction_date >= params.date_from)
        if params.date_to:
            stmt = stmt.where(self.model.transaction_date <= params.date_to)
        return stmt

    async def sum_by_filters(self, params: LedgerQuery) -> dict:
        """同濾鏡的**全量**收支合計 —— 統計卡用。

        2026-08-29 owner「統計圖卡＋掌握年度資金」通盤檢視：本頁卡片原本
        由前端 reduce 當頁 items（≤limit 筆），只能誠實標成「本頁收入」——
        分頁前 SQL SUM 才是卡片該有的分母（同 client-accounts totals 修法）。
        """
        from decimal import Decimal

        stmt = select(
            self.model.entry_type,
            func.coalesce(func.sum(self.model.amount), 0).label("total"),
        )
        stmt = self._apply_query_filters(stmt, params).group_by(self.model.entry_type)
        rows = (await self.db.execute(stmt)).all()
        sums = {"income": Decimal("0"), "expense": Decimal("0")}
        for entry_type, total in rows:
            if entry_type in sums:
                sums[entry_type] = total
        return {
            "income": str(sums["income"]),
            "expense": str(sums["expense"]),
            "net": str(sums["income"] - sums["expense"]),
        }

    async def query(self, params: LedgerQuery) -> Tuple[List[FinanceLedger], int]:
        stmt = select(self.model)
        stmt = self._apply_query_filters(stmt, params)

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
        """新增帳本記錄 (flush only — 由呼叫端控制 commit 以確保交易原子性)

        ADR-0013 Phase 2: 若無 ledger_code 則自動生成 FL_{yyyy}_{NNNNN}。
        所有 record_from_* 入帳路徑均經過此方法，集中注入確保覆蓋率。
        使用 savepoint + retry 處理併發 unique constraint 衝突。
        """
        from app.services.coding_helpers import retry_on_code_conflict

        async def _add_and_flush() -> FinanceLedger:
            if not getattr(ledger, "ledger_code", None):
                from app.services.contract import CaseCodeService
                year = (ledger.transaction_date.year
                        if ledger.transaction_date else date.today().year)
                code_svc = CaseCodeService(self.db)
                ledger.ledger_code = await code_svc.generate_ledger_code(year=year)

            self.db.add(ledger)
            await self.db.flush()
            await self.db.refresh(ledger)
            return ledger

        return await retry_on_code_conflict(
            self.db, _add_and_flush, unique_field="ledger_code"
        )

    async def delete_entry(self, ledger: FinanceLedger) -> bool:
        """刪除帳本記錄"""
        await self.db.delete(ledger)
        await self.db.flush()
        await self.db.commit()
        return True
