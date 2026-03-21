from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import date
from decimal import Decimal

from app.extended.models.core import ContractProject
from app.extended.models.invoice import ExpenseInvoice
from app.extended.models.finance import FinanceLedger
from app.schemas.erp.financial_summary import ProjectFinancialSummary, CompanyFinancialOverview

class FinancialSummaryRepository:
    """跨模組財務彙總與統計，透過 JOIN 各資料表"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_summary(self, case_code: str) -> Optional[ProjectFinancialSummary]:
        """抓取單一專案的預算/收支狀態"""
        # 1. 取得專案主檔資訊 (ContractProject)
        stmt_proj = select(ContractProject).where(ContractProject.project_code == case_code)
        proj = (await self.db.execute(stmt_proj)).scalars().first()
        if not proj:
            return None

        # 2. ExpenseInvoice 統計
        stmt_expense = select(
            func.count(ExpenseInvoice.id),
            func.sum(ExpenseInvoice.amount)
        ).where(ExpenseInvoice.case_code == case_code)
        expense_res = (await self.db.execute(stmt_expense)).first()
        exp_count = expense_res[0] or 0
        exp_total = expense_res[1] or Decimal("0")

        # 3. FinanceLedger 統計
        stmt_ledger = select(
            FinanceLedger.entry_type,
            func.sum(FinanceLedger.amount)
        ).where(FinanceLedger.case_code == case_code).group_by(FinanceLedger.entry_type)
        ledger_res = (await self.db.execute(stmt_ledger)).all()
        
        income = Decimal("0")
        expense = Decimal("0")
        for r in ledger_res:
            if r.entry_type == "income":
                income = r[1] or Decimal("0")
            elif r.entry_type == "expense":
                expense = r[1] or Decimal("0")

        net_balance = income - expense
        
        # NOTE: 此處若有 ERPQuotation / ERPBilling 也可以平行 JOIN。目前實作核心 Ledger。
        budget = Decimal(str(proj.contract_amount)) if proj.contract_amount else None
        used_perc = float((expense / budget) * 100) if budget and budget > 0 else None
        
        alert = "normal"
        if used_perc:
            if used_perc > 95:
                alert = "critical"
            elif used_perc > 80:
                alert = "warning"

        return ProjectFinancialSummary(
            case_code=case_code,
            case_name=proj.project_name,
            budget_total=budget,
            expense_invoice_count=exp_count,
            expense_invoice_total=exp_total,
            total_income=income,
            total_expense=expense,
            net_balance=net_balance,
            budget_used_percentage=used_perc,
            budget_alert=alert
        )

    async def get_company_overview(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        top_n: int = 10,
    ) -> dict:
        """全公司財務總覽 — 收支彙總 + 分類拆解"""
        from sqlalchemy import and_, case as sa_case

        conditions = []
        if date_from:
            conditions.append(FinanceLedger.transaction_date >= date_from)
        if date_to:
            conditions.append(FinanceLedger.transaction_date <= date_to)

        where_clause = and_(*conditions) if conditions else True

        # 1. 收支彙總
        stmt_totals = select(
            func.sum(
                sa_case((FinanceLedger.entry_type == "income", FinanceLedger.amount), else_=Decimal("0"))
            ).label("total_income"),
            func.sum(
                sa_case((FinanceLedger.entry_type == "expense", FinanceLedger.amount), else_=Decimal("0"))
            ).label("total_expense"),
        ).where(where_clause)

        totals = (await self.db.execute(stmt_totals)).first()
        total_income = totals.total_income or Decimal("0")
        total_expense = totals.total_expense or Decimal("0")

        # 2. 支出分類拆解
        stmt_by_cat = (
            select(
                FinanceLedger.category,
                func.sum(FinanceLedger.amount).label("cat_total"),
            )
            .where(and_(FinanceLedger.entry_type == "expense", *conditions))
            .group_by(FinanceLedger.category)
            .order_by(func.sum(FinanceLedger.amount).desc())
        )
        cat_rows = (await self.db.execute(stmt_by_cat)).all()
        expense_by_category = {
            (r.category or "未分類"): r.cat_total or Decimal("0")
            for r in cat_rows
        }

        # 3. 專案 vs 營運支出
        stmt_proj_exp = (
            select(func.sum(FinanceLedger.amount))
            .where(and_(
                FinanceLedger.entry_type == "expense",
                FinanceLedger.case_code.isnot(None),
                *conditions,
            ))
        )
        project_expense = (await self.db.scalar(stmt_proj_exp)) or Decimal("0")
        operation_expense = total_expense - project_expense

        return {
            "period_start": date_from or date(2020, 1, 1),
            "period_end": date_to or date.today(),
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": total_income - total_expense,
            "expense_by_category": expense_by_category,
            "project_expense": project_expense,
            "operation_expense": operation_expense,
            "top_projects": [],  # 由 Service 層填充
        }
