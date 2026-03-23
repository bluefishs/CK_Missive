from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case as sa_case, extract
from typing import List, Optional, Tuple
from datetime import date
from decimal import Decimal

from app.extended.models.core import ContractProject
from app.extended.models.erp import ERPQuotation
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

    async def get_batch_project_summaries(
        self, case_codes: List[str]
    ) -> List[Optional[ProjectFinancialSummary]]:
        """批量取得多專案財務彙總 — 避免 N+1 查詢

        用 3 批量查詢取代 N*3 逐筆查詢：
        1. 一次查所有 ContractProject
        2. 一次 GROUP BY 所有 ExpenseInvoice
        3. 一次 GROUP BY 所有 FinanceLedger
        """
        if not case_codes:
            return []

        # 1. 批量取專案主檔
        stmt_proj = select(ContractProject).where(
            ContractProject.project_code.in_(case_codes)
        )
        proj_rows = (await self.db.execute(stmt_proj)).scalars().all()
        proj_map = {p.project_code: p for p in proj_rows}

        # 2. 批量取 ExpenseInvoice 統計
        stmt_expense = (
            select(
                ExpenseInvoice.case_code,
                func.count(ExpenseInvoice.id).label("cnt"),
                func.sum(ExpenseInvoice.amount).label("total"),
            )
            .where(ExpenseInvoice.case_code.in_(case_codes))
            .group_by(ExpenseInvoice.case_code)
        )
        expense_rows = (await self.db.execute(stmt_expense)).all()
        expense_map = {r.case_code: r for r in expense_rows}

        # 3. 批量取 Ledger 統計
        stmt_ledger = (
            select(
                FinanceLedger.case_code,
                FinanceLedger.entry_type,
                func.sum(FinanceLedger.amount).label("total"),
            )
            .where(FinanceLedger.case_code.in_(case_codes))
            .group_by(FinanceLedger.case_code, FinanceLedger.entry_type)
        )
        ledger_rows = (await self.db.execute(stmt_ledger)).all()
        ledger_map: dict = {}
        for r in ledger_rows:
            ledger_map.setdefault(r.case_code, {})[r.entry_type] = r.total or Decimal("0")

        # 4. 組裝結果（保留原始順序）
        results = []
        for cc in case_codes:
            proj = proj_map.get(cc)
            if not proj:
                results.append(None)
                continue

            exp = expense_map.get(cc)
            exp_count = exp.cnt if exp else 0
            exp_total = exp.total or Decimal("0") if exp else Decimal("0")

            ledger_entry = ledger_map.get(cc, {})
            income = ledger_entry.get("income", Decimal("0"))
            expense_amt = ledger_entry.get("expense", Decimal("0"))
            net_balance = income - expense_amt

            budget = Decimal(str(proj.contract_amount)) if proj.contract_amount else None
            used_perc = float((expense_amt / budget) * 100) if budget and budget > 0 else None

            alert = "normal"
            if used_perc:
                if used_perc > 95:
                    alert = "critical"
                elif used_perc > 80:
                    alert = "warning"

            results.append(ProjectFinancialSummary(
                case_code=cc,
                case_name=proj.project_name,
                budget_total=budget,
                expense_invoice_count=exp_count,
                expense_invoice_total=exp_total,
                total_income=income,
                total_expense=expense_amt,
                net_balance=net_balance,
                budget_used_percentage=used_perc,
                budget_alert=alert,
            ))

        return results

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

    async def get_case_codes_paginated(
        self, year: Optional[int] = None, skip: int = 0, limit: int = 20
    ) -> Tuple[List[str], int]:
        """從 ERPQuotation 取分頁案號列表及總數"""
        conditions = []
        if year:
            conditions.append(ERPQuotation.year == year)

        # 案號列表
        stmt = select(ERPQuotation.case_code)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(ERPQuotation.case_code).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        case_codes = [row[0] for row in result.all()]

        # 總數
        count_stmt = select(func.count()).select_from(ERPQuotation)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = await self.db.scalar(count_stmt) or 0

        return case_codes, total

    async def get_top_expense_projects(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        top_n: int = 10,
    ) -> List[str]:
        """取得支出最高的 Top N 案號"""
        conditions = [
            FinanceLedger.case_code.isnot(None),
            FinanceLedger.entry_type == "expense",
        ]
        if date_from:
            conditions.append(FinanceLedger.transaction_date >= date_from)
        if date_to:
            conditions.append(FinanceLedger.transaction_date <= date_to)

        stmt = (
            select(FinanceLedger.case_code)
            .where(and_(*conditions))
            .group_by(FinanceLedger.case_code)
            .order_by(func.sum(FinanceLedger.amount).desc())
            .limit(top_n)
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_monthly_trend(
        self,
        months: int = 12,
        case_code: Optional[str] = None,
    ) -> List[dict]:
        """月度收支趨勢 — 回溯 N 個月的收入/支出/淨額

        Returns:
            [{"month": "2026-03", "income": Decimal, "expense": Decimal, "net": Decimal}, ...]
        """
        from dateutil.relativedelta import relativedelta

        end_date = date.today()
        start_date = end_date - relativedelta(months=months - 1)
        start_date = start_date.replace(day=1)

        conditions = [
            FinanceLedger.transaction_date >= start_date,
            FinanceLedger.transaction_date <= end_date,
        ]
        if case_code:
            conditions.append(FinanceLedger.case_code == case_code)

        # 使用 literal_column 避免 asyncpg 在 SELECT 和 GROUP BY 產生不同參數索引，
        # 導致 PostgreSQL 回傳 GroupingError。
        from sqlalchemy import literal_column
        month_fmt = literal_column("'YYYY-MM'")
        month_expr = func.to_char(FinanceLedger.transaction_date, month_fmt).label("month")

        stmt = (
            select(
                month_expr,
                func.sum(
                    sa_case(
                        (FinanceLedger.entry_type == "income", FinanceLedger.amount),
                        else_=Decimal("0"),
                    )
                ).label("income"),
                func.sum(
                    sa_case(
                        (FinanceLedger.entry_type == "expense", FinanceLedger.amount),
                        else_=Decimal("0"),
                    )
                ).label("expense"),
            )
            .where(and_(*conditions))
            .group_by(func.to_char(FinanceLedger.transaction_date, month_fmt))
            .order_by(func.to_char(FinanceLedger.transaction_date, month_fmt))
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        # 補全空月份
        trend = []
        current = start_date
        data_map = {r.month: r for r in rows}
        while current <= end_date:
            key = current.strftime("%Y-%m")
            if key in data_map:
                r = data_map[key]
                inc = r.income or Decimal("0")
                exp = r.expense or Decimal("0")
            else:
                inc = Decimal("0")
                exp = Decimal("0")
            trend.append({
                "month": key,
                "income": inc,
                "expense": exp,
                "net": inc - exp,
            })
            current = (current + relativedelta(months=1))

        return trend

    async def get_budget_ranking(
        self,
        top_n: int = 15,
        order_desc: bool = True,
    ) -> Tuple[List[dict], int]:
        """預算使用率排行 — 各專案支出/收入比

        Returns:
            (items, total_projects)
        """
        # 從 FinanceLedger GROUP BY case_code 取收支
        stmt = (
            select(
                FinanceLedger.case_code,
                func.sum(
                    sa_case(
                        (FinanceLedger.entry_type == "income", FinanceLedger.amount),
                        else_=Decimal("0"),
                    )
                ).label("total_income"),
                func.sum(
                    sa_case(
                        (FinanceLedger.entry_type == "expense", FinanceLedger.amount),
                        else_=Decimal("0"),
                    )
                ).label("total_expense"),
            )
            .where(FinanceLedger.case_code.isnot(None))
            .group_by(FinanceLedger.case_code)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        # 計算 usage_pct 並排序
        items = []
        for r in rows:
            income = float(r.total_income or 0)
            expense = float(r.total_expense or 0)
            usage_pct = (expense / income * 100) if income > 0 else None

            alert = "normal"
            if usage_pct is not None:
                if usage_pct >= 100:
                    alert = "critical"
                elif usage_pct >= 80:
                    alert = "warning"

            items.append({
                "case_code": r.case_code,
                "total_income": r.total_income or Decimal("0"),
                "total_expense": r.total_expense or Decimal("0"),
                "usage_pct": round(usage_pct, 1) if usage_pct is not None else None,
                "alert": alert,
            })

        # 排序 (None usage_pct 排最後)
        items.sort(
            key=lambda x: x["usage_pct"] if x["usage_pct"] is not None else -1,
            reverse=order_desc,
        )

        total = len(items)
        return items[:top_n], total
