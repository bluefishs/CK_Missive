"""跨模組財務彙總 Service — 專案 + 全公司總覽"""
import logging
from datetime import date
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

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
        case_codes, total = await self.repo.get_case_codes_paginated(
            year=year, skip=skip, limit=limit
        )

        # 批量查詢各案彙總
        summaries = []
        for cc in case_codes:
            summary = await self.repo.get_project_summary(cc)
            summaries.append(summary)

        return {"items": summaries, "total": total, "skip": skip, "limit": limit}

    async def get_monthly_trend(
        self,
        months: int = 12,
        case_code: Optional[str] = None,
    ) -> dict:
        """月度收支趨勢"""
        trend = await self.repo.get_monthly_trend(months=months, case_code=case_code)
        return {"months": trend, "case_code": case_code}

    async def get_budget_ranking(
        self,
        top_n: int = 15,
        order_desc: bool = True,
    ) -> dict:
        """預算使用率排行"""
        items, total = await self.repo.get_budget_ranking(
            top_n=top_n, order_desc=order_desc
        )

        # 批量補充案名+預算 (避免 N+1 查詢)
        from app.extended.models.core import ContractProject
        from sqlalchemy import select

        case_codes = [item["case_code"] for item in items if item.get("case_code")]
        if case_codes:
            stmt = select(
                ContractProject.project_code,
                ContractProject.project_name,
                ContractProject.contract_amount,
            ).where(ContractProject.project_code.in_(case_codes))
            result = await self.db.execute(stmt)
            project_map = {
                row.project_code: row for row in result.all()
            }
        else:
            project_map = {}

        for item in items:
            proj = project_map.get(item.get("case_code"))
            item["case_name"] = proj.project_name if proj else None
            item["budget_total"] = proj.contract_amount if proj else None

        return {"items": items, "total_projects": total}

    async def _get_top_projects(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        top_n: int = 10,
    ) -> List[dict]:
        """取得支出最高的 Top N 專案"""
        top_case_codes = await self.repo.get_top_expense_projects(
            date_from=date_from, date_to=date_to, top_n=top_n
        )

        # 各案取完整彙總
        summaries = []
        for cc in top_case_codes:
            summary = await self.repo.get_project_summary(cc)
            summaries.append(summary)

        return summaries
