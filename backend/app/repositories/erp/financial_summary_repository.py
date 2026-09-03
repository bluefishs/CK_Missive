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
        """抓取單一專案的預算/收支狀態 —— 委派批量版（2026-09-04：兩份實作各自把
        `ContractProject.project_code` 拿去對 case_code，PM 制成案後永遠對不到；只留一份）。"""
        rows = await self.get_batch_project_summaries([case_code])
        return rows[0] if rows else None

    async def get_batch_project_summaries(
        self, case_codes: List[str]
    ) -> List[Optional[ProjectFinancialSummary]]:
        """批量取得多專案財務彙總 — 6 批量查詢取代 N×6 逐筆。

        ⚠️ 2026-09-04 金流複查：主檔此前用 `ContractProject.project_code.in_(case_codes)` 去對
        帳本／報價單的 **case_code** —— PM 制成案後兩者不同（`CK2025_PM_02_108` vs `CK2025_02_108`）。
        實測帳本 49 個案號用 case_code 對得到 48、用 project_code 只對得到 3 ⇒ 財務儀表板的
        「專案財務一覽」只剩 34 筆舊制案、其餘全被當「找不到主檔」丟掉，而 total 照數（131 筆／畫面 17 列）。
        案號橋樑同族第十二處。另 `quotation_total`／請款／實收／應付四欄 schema 有、這裡從未填 ⇒ 畫面永遠 0。
        """
        if not case_codes:
            return []
        from app.extended.models.erp import ERPBilling, ERPVendorPayable

        # 1. 主檔：以 case_code（跨模組橋樑）對；舊制 project_code=case_code 也在這條路上
        stmt_proj = select(ContractProject).where(ContractProject.case_code.in_(case_codes))
        proj_rows = (await self.db.execute(stmt_proj)).scalars().all()
        proj_map = {p.case_code: p for p in proj_rows}

        # 2. ExpenseInvoice
        stmt_expense = (
            select(
                ExpenseInvoice.case_code,
                func.count(ExpenseInvoice.id).label("cnt"),
                func.sum(ExpenseInvoice.amount).label("total"),
            )
            .where(ExpenseInvoice.case_code.in_(case_codes))
            .group_by(ExpenseInvoice.case_code)
        )
        expense_map = {r.case_code: r for r in (await self.db.execute(stmt_expense)).all()}

        # 3. Ledger
        stmt_ledger = (
            select(
                FinanceLedger.case_code,
                FinanceLedger.entry_type,
                func.sum(FinanceLedger.amount).label("total"),
            )
            .where(FinanceLedger.case_code.in_(case_codes))
            .group_by(FinanceLedger.case_code, FinanceLedger.entry_type)
        )
        ledger_map: dict = {}
        for r in (await self.db.execute(stmt_ledger)).all():
            ledger_map.setdefault(r.case_code, {})[r.entry_type] = r.total or Decimal("0")

        # 4. 報價單：未刪；同案多版取「已成案的那張」，否則取最新
        stmt_quot = (
            select(ERPQuotation.case_code, ERPQuotation.id, ERPQuotation.project_code, ERPQuotation.total_price)
            .where(ERPQuotation.case_code.in_(case_codes), ERPQuotation.deleted_at.is_(None))
            .order_by(ERPQuotation.case_code, ERPQuotation.id)
        )
        quot_pick: dict = {}
        for r in (await self.db.execute(stmt_quot)).all():
            cur = quot_pick.get(r.case_code)
            if (cur is None or (r.project_code and not cur.project_code)
                    or (bool(r.project_code) == bool(cur.project_code) and r.id > cur.id)):
                quot_pick[r.case_code] = r

        # 5. 請款／實收、應付／已付 —— 金流掛在報價單上，按 case_code 匯總（版次全算，分身已合併）
        stmt_bill = (
            select(
                ERPQuotation.case_code,
                func.coalesce(func.sum(ERPBilling.billing_amount), 0).label("billed"),
                func.coalesce(func.sum(ERPBilling.payment_amount), 0).label("received"),
            )
            .join(ERPQuotation, ERPQuotation.id == ERPBilling.erp_quotation_id)
            .where(ERPQuotation.case_code.in_(case_codes), ERPQuotation.deleted_at.is_(None))
            .group_by(ERPQuotation.case_code)
        )
        bill_map = {r.case_code: r for r in (await self.db.execute(stmt_bill)).all()}
        stmt_pay = (
            select(
                ERPQuotation.case_code,
                func.coalesce(func.sum(ERPVendorPayable.payable_amount), 0).label("payable"),
                func.coalesce(func.sum(ERPVendorPayable.paid_amount), 0).label("paid"),
            )
            .join(ERPQuotation, ERPQuotation.id == ERPVendorPayable.erp_quotation_id)
            .where(ERPQuotation.case_code.in_(case_codes), ERPQuotation.deleted_at.is_(None))
            .group_by(ERPQuotation.case_code)
        )
        pay_map = {r.case_code: r for r in (await self.db.execute(stmt_pay)).all()}

        # 6. 組裝（保留原始順序）
        results: List[Optional[ProjectFinancialSummary]] = []
        for cc in case_codes:
            proj = proj_map.get(cc)
            if not proj:
                results.append(None)
                continue
            exp = expense_map.get(cc)
            exp_count = exp.cnt if exp else 0
            exp_total = (exp.total or Decimal("0")) if exp else Decimal("0")
            ledger_entry = ledger_map.get(cc, {})
            income = ledger_entry.get("income", Decimal("0"))
            expense_amt = ledger_entry.get("expense", Decimal("0"))
            budget = Decimal(str(proj.contract_amount)) if proj.contract_amount else None
            used_perc = float((expense_amt / budget) * 100) if budget and budget > 0 else None
            alert = "normal"
            if used_perc:
                if used_perc > 95:
                    alert = "critical"
                elif used_perc > 80:
                    alert = "warning"
            qp = quot_pick.get(cc)
            bl = bill_map.get(cc)
            pa = pay_map.get(cc)
            results.append(ProjectFinancialSummary(
                case_code=cc,
                project_code=proj.project_code or (qp.project_code if qp else None),
                case_name=proj.project_name,
                erp_quotation_id=qp.id if qp else None,
                budget_total=budget,
                quotation_total=Decimal(str(qp.total_price)) if qp and qp.total_price is not None else None,
                billed_amount=Decimal(str(bl.billed)) if bl else Decimal("0"),
                received_amount=Decimal(str(bl.received)) if bl else Decimal("0"),
                vendor_payable_total=Decimal(str(pa.payable)) if pa else Decimal("0"),
                vendor_paid_total=Decimal(str(pa.paid)) if pa else Decimal("0"),
                expense_invoice_count=exp_count,
                expense_invoice_total=exp_total,
                total_income=income,
                total_expense=expense_amt,
                net_balance=income - expense_amt,
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
        """分頁案號 —— 來源是**承攬案**（成案才有「專案財務一覽」的意義）。

        2026-09-04 前從報價單取：含已刪、同案多版重複，且 total 是報價單張數不是案數 ⇒
        畫面「131 筆」只列 17 列。年度＝案件年**或**報價單年任一命中（財務頁口徑是報價單年，
        GN 標案沒有報價單就看案件年）。
        """
        from sqlalchemy import or_

        stmt = select(ContractProject.case_code)
        if year:
            same_year_quote = (
                select(ERPQuotation.id)
                .where(ERPQuotation.case_code == ContractProject.case_code,
                       ERPQuotation.year == year,
                       ERPQuotation.deleted_at.is_(None))
                .exists()
            )
            stmt = stmt.where(or_(ContractProject.year == year, same_year_quote))
        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = (await self.db.execute(
            stmt.order_by(ContractProject.case_code.desc()).offset(skip).limit(limit)
        )).all()
        return [r[0] for r in rows], total

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

    async def get_aging_analysis(
        self,
        direction: str = "receivable",
        year: Optional[int] = None,
    ) -> dict:
        """應收/應付帳齡分析 — 按天數分組: 0-30/31-60/61-90/90+"""
        from app.extended.models.erp import ERPBilling, ERPVendorPayable

        today = date.today()

        if direction == "receivable":
            # 應收: 未完成收款的 billing
            query = (
                select(
                    ERPBilling.billing_date,
                    ERPBilling.billing_amount,
                    ERPBilling.payment_amount,
                )
                .join(ERPQuotation, ERPBilling.erp_quotation_id == ERPQuotation.id)
                .where(ERPBilling.payment_status.in_(["pending", "partial", "overdue"]))
            )
            if year:
                query = query.where(ERPQuotation.year == year)
        else:
            # 應付: 未完成付款的 vendor_payable
            query = (
                select(
                    ERPVendorPayable.due_date,
                    ERPVendorPayable.payable_amount,
                    ERPVendorPayable.paid_amount,
                )
                .join(ERPQuotation, ERPVendorPayable.erp_quotation_id == ERPQuotation.id)
                .where(ERPVendorPayable.payment_status.in_(["unpaid", "partial"]))
            )
            if year:
                query = query.where(ERPQuotation.year == year)

        result = await self.db.execute(query)
        rows = result.all()

        buckets = {
            "0-30": {"count": 0, "amount": Decimal("0")},
            "31-60": {"count": 0, "amount": Decimal("0")},
            "61-90": {"count": 0, "amount": Decimal("0")},
            "90+": {"count": 0, "amount": Decimal("0")},
        }

        for row in rows:
            ref_date = row[0]  # billing_date or due_date
            total_amount = row[1] or Decimal("0")
            paid = row[2] or Decimal("0")
            outstanding = total_amount - paid

            if ref_date is None:
                days = 999
            else:
                days = (today - ref_date).days

            if days <= 30:
                bucket_key = "0-30"
            elif days <= 60:
                bucket_key = "31-60"
            elif days <= 90:
                bucket_key = "61-90"
            else:
                bucket_key = "90+"

            buckets[bucket_key]["count"] += 1
            buckets[bucket_key]["amount"] += outstanding

        return buckets
