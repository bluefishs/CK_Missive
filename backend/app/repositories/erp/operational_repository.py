"""營運帳目 Repository

帳目主檔 + 費用明細的資料存取層
"""
import logging
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base_repository import BaseRepository
from app.extended.models.operational import OperationalAccount, OperationalExpense
from app.schemas.erp.operational import (
    OperationalAccountListRequest,
    OperationalExpenseListRequest,
    ACCOUNT_CATEGORY_CODES,
)

logger = logging.getLogger(__name__)


class OperationalAccountRepository(BaseRepository[OperationalAccount]):
    """營運帳目主檔 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, OperationalAccount)

    async def list_filtered(
        self, params: OperationalAccountListRequest
    ) -> Tuple[List[OperationalAccount], int]:
        """篩選帳目列表"""
        stmt = select(self.model)

        if params.category:
            stmt = stmt.where(self.model.category == params.category)
        if params.fiscal_year:
            stmt = stmt.where(self.model.fiscal_year == params.fiscal_year)
        if params.status:
            stmt = stmt.where(self.model.status == params.status)
        if params.keyword:
            kw = f"%{params.keyword}%"
            stmt = stmt.where(
                self.model.name.ilike(kw) | self.model.account_code.ilike(kw)
            )

        count_query = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_query) or 0

        stmt = stmt.order_by(self.model.created_at.desc()).offset(params.skip).limit(params.limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def get_total_spent(self, account_id: int) -> Decimal:
        """取得帳目累計支出 (僅核准項目)"""
        stmt = select(func.coalesce(func.sum(OperationalExpense.amount), 0)).where(
            and_(
                OperationalExpense.account_id == account_id,
                OperationalExpense.approval_status == "approved",
            )
        )
        result = await self.db.scalar(stmt)
        return Decimal(str(result)) if result else Decimal("0")

    async def generate_code(self, fiscal_year: int, category: str) -> str:
        """產生帳目編號: OP_{fiscal_year}_{CATEGORY_CODE}_{3-digit seq}"""
        category_code = ACCOUNT_CATEGORY_CODES.get(category, "MS")
        prefix = f"OP_{fiscal_year}_{category_code}_"

        stmt = (
            select(self.model.account_code)
            .where(self.model.account_code.like(f"{prefix}%"))
            .order_by(self.model.account_code.desc())
            .limit(1)
        )
        result = await self.db.scalar(stmt)

        if result:
            try:
                seq = int(result.split("_")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f"{prefix}{seq:03d}"

    async def get_stats(
        self, fiscal_year: Optional[int] = None
    ) -> dict:
        """取得統計數據"""
        # Base filters
        acct_filter = []
        if fiscal_year:
            acct_filter.append(self.model.fiscal_year == fiscal_year)

        # Total accounts
        stmt_count = select(func.count(self.model.id))
        if acct_filter:
            stmt_count = stmt_count.where(*acct_filter)
        total_accounts = await self.db.scalar(stmt_count) or 0

        # Total budget
        stmt_budget = select(func.coalesce(func.sum(self.model.budget_limit), 0))
        if acct_filter:
            stmt_budget = stmt_budget.where(*acct_filter)
        total_budget = await self.db.scalar(stmt_budget) or Decimal("0")

        # Total spent (approved expenses)
        spent_stmt = (
            select(func.coalesce(func.sum(OperationalExpense.amount), 0))
            .select_from(OperationalExpense)
            .join(OperationalAccount)
            .where(OperationalExpense.approval_status == "approved")
        )
        if fiscal_year:
            spent_stmt = spent_stmt.where(OperationalAccount.fiscal_year == fiscal_year)
        total_spent = await self.db.scalar(spent_stmt) or Decimal("0")

        # By category
        cat_stmt = (
            select(
                self.model.category,
                func.coalesce(func.sum(self.model.budget_limit), 0).label("budget"),
            )
            .group_by(self.model.category)
        )
        if acct_filter:
            cat_stmt = cat_stmt.where(*acct_filter)
        cat_result = await self.db.execute(cat_stmt)
        by_category = {}
        for row in cat_result:
            cat = row[0]
            budget = Decimal(str(row[1]))
            # Get spent per category
            cat_spent_stmt = (
                select(func.coalesce(func.sum(OperationalExpense.amount), 0))
                .select_from(OperationalExpense)
                .join(OperationalAccount)
                .where(
                    and_(
                        OperationalAccount.category == cat,
                        OperationalExpense.approval_status == "approved",
                    )
                )
            )
            if fiscal_year:
                cat_spent_stmt = cat_spent_stmt.where(
                    OperationalAccount.fiscal_year == fiscal_year
                )
            spent = await self.db.scalar(cat_spent_stmt) or Decimal("0")
            by_category[cat] = {"budget": budget, "spent": Decimal(str(spent))}

        return {
            "total_accounts": total_accounts,
            "total_budget": Decimal(str(total_budget)),
            "total_spent": Decimal(str(total_spent)),
            "by_category": by_category,
        }


class OperationalExpenseRepository(BaseRepository[OperationalExpense]):
    """營運費用明細 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, OperationalExpense)

    async def list_filtered(
        self, params: OperationalExpenseListRequest
    ) -> Tuple[List[OperationalExpense], int]:
        """篩選費用列表"""
        stmt = select(self.model)

        if params.account_id:
            stmt = stmt.where(self.model.account_id == params.account_id)
        if params.category:
            stmt = stmt.where(self.model.category == params.category)
        if params.date_from:
            stmt = stmt.where(self.model.expense_date >= params.date_from)
        if params.date_to:
            stmt = stmt.where(self.model.expense_date <= params.date_to)
        if params.approval_status:
            stmt = stmt.where(self.model.approval_status == params.approval_status)

        count_query = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_query) or 0

        stmt = stmt.order_by(self.model.expense_date.desc()).offset(params.skip).limit(params.limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def approve(self, expense_id: int, approved_by: int) -> Optional[OperationalExpense]:
        """核准費用"""
        from datetime import datetime as dt

        expense = await self.get_by_id(expense_id)
        if not expense:
            return None
        if expense.approval_status != "pending":
            return None

        expense.approval_status = "approved"
        expense.approved_by = approved_by
        expense.approved_at = dt.now()
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def reject(
        self, expense_id: int, reason: Optional[str] = None
    ) -> Optional[OperationalExpense]:
        """駁回費用"""
        expense = await self.get_by_id(expense_id)
        if not expense:
            return None
        if expense.approval_status != "pending":
            return None

        expense.approval_status = "rejected"
        if reason:
            expense.notes = (
                f"{expense.notes}\n駁回原因: {reason}" if expense.notes else f"駁回原因: {reason}"
            )
        await self.db.flush()
        await self.db.refresh(expense)
        return expense
