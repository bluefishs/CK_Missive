"""跨模組財務彙總 Service — 專案 + 全公司總覽"""
import logging
from datetime import date
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.extended.models.erp import ERPQuotation
from app.extended.models.finance import FinanceLedger
from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository

logger = logging.getLogger(__name__)


class FinancialSummaryService:
    """跨模組財務彙總業務邏輯

    職責：
    - 單一專案財務彙總 (ERP + 報銷 + 帳本)
    - 全公司財務總覽 (收支 + 分類 + Top N)
    - 民國年度轉換
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FinancialSummaryRepository(db)

    async def get_project_summary(self, case_code: str) -> dict:
        """取得單一專案完整財務彙總"""
        return await self.repo.get_project_summary(case_code)

    async def get_company_overview(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        year: Optional[int] = None,
        top_n: int = 10,
    ) -> dict:
        """全公司財務總覽"""
        # 民國年度轉西元日期區間
        if year and not date_from and not date_to:
            ad_year = year + 1911
            date_from = date(ad_year, 1, 1)
            date_to = date(ad_year, 12, 31)

        overview = await self.repo.get_company_overview(
            date_from=date_from, date_to=date_to, top_n=top_n
        )

        # 填充 Top N 專案
        top_projects = await self._get_top_projects(
            date_from=date_from, date_to=date_to, top_n=top_n
        )
        overview["top_projects"] = top_projects

        return overview

    async def get_all_projects_summary(
        self, year: Optional[int] = None, skip: int = 0, limit: int = 20
    ) -> dict:
        """所有專案財務一覽"""
        # 取得有效案號列表
        conditions = []
        if year:
            conditions.append(ERPQuotation.year == year)

        stmt = (
            select(ERPQuotation.case_code)
            .where(*conditions) if conditions else select(ERPQuotation.case_code)
        )
        stmt = stmt.order_by(ERPQuotation.case_code).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        case_codes = [row[0] for row in result.all()]

        # 逐案彙總
        summaries = []
        for cc in case_codes:
            summary = await self.repo.get_project_summary(cc)
            summaries.append(summary)

        # 總數
        count_stmt = select(func.count()).select_from(ERPQuotation)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        return {"items": summaries, "total": total, "skip": skip, "limit": limit}

    async def _get_top_projects(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        top_n: int = 10,
    ) -> List[dict]:
        """取得支出最高的 Top N 專案"""
        conditions = [
            FinanceLedger.case_code.isnot(None),
            FinanceLedger.entry_type == "expense",
        ]
        if date_from:
            conditions.append(FinanceLedger.transaction_date >= date_from)
        if date_to:
            conditions.append(FinanceLedger.transaction_date <= date_to)

        from sqlalchemy import and_

        stmt = (
            select(
                FinanceLedger.case_code,
                func.sum(FinanceLedger.amount).label("total_expense"),
            )
            .where(and_(*conditions))
            .group_by(FinanceLedger.case_code)
            .order_by(func.sum(FinanceLedger.amount).desc())
            .limit(top_n)
        )
        result = await self.db.execute(stmt)
        top_cases = result.all()

        # 各案取完整彙總
        summaries = []
        for row in top_cases:
            summary = await self.repo.get_project_summary(row.case_code)
            summaries.append(summary)

        return summaries
