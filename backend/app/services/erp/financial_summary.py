"""跨模組財務彙總 Service — 專案 + 全公司總覽"""
import logging
from datetime import date
from decimal import Decimal
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
        # 2026-08-29 owner 裁示：**系統統一採西元年建置資料與查詢服務**。
        #
        # 此處原為 `ad_year = year + 1911`（收民國年）—— 而同一支 service 的
        # `get_all_projects_summary` 走的 repo 是直接比對 `ERPQuotation.year`
        # （西元）⇒ **同一個 service 兩種紀年契約**，正是 08-29 一天抓到四個
        # 「年度篩選從未生效」的土壤（client-accounts／vendor-accounts／
        # 財務總覽／發票彙總）。
        #
        # 現在一律收西元。⚠️ 相容處理：DB 的 year 欄位全部是西元（實查
        # pm_cases／contract_projects 無任何 115 之類的值），所以收到 <1911
        # 的值只可能是舊客戶端送民國年 —— 轉換並**出聲**，不靜默接受。
        if year and not date_from and not date_to:
            if year < 1911:
                logger.warning(
                    "get_company_overview 收到民國年 %s —— 系統已統一西元"
                    "（owner 2026-08-29 裁示），請修正呼叫端；本次自動轉換為 %s",
                    year, year + 1911,
                )
                year = year + 1911
            date_from = date(year, 1, 1)
            date_to = date(year, 12, 31)

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

        # 批量查詢各案彙總 (3 queries 取代 N*3)
        summaries = await self.repo.get_batch_project_summaries(case_codes)
        # 過濾 None（找不到專案主檔的案號）
        summaries = [s for s in summaries if s is not None]

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
        """預算使用率排行。

        2026-09-04：案名／合約額此前用 `ContractProject.project_code` 對帳本的 case_code ⇒ PM 制永遠 None
        （同族十二）。且名字叫「預算使用率」而分母是收入 —— 有合約額就用合約額，沒有才退回收入
        （repo 的算法），並在**補完分母之後**才排序取 top_n（此前 repo 先截斷再補資料，順序是錯的）。
        """
        from app.extended.models.core import ContractProject
        from sqlalchemy import select

        items, total = await self.repo.get_budget_ranking(top_n=10**6, order_desc=order_desc)

        case_codes = [item["case_code"] for item in items if item.get("case_code")]
        project_map = {}
        if case_codes:
            stmt = select(
                ContractProject.case_code,
                ContractProject.project_name,
                ContractProject.contract_amount,
            ).where(ContractProject.case_code.in_(case_codes))
            project_map = {row.case_code: row for row in (await self.db.execute(stmt)).all()}

        for item in items:
            proj = project_map.get(item.get("case_code"))
            item["case_name"] = proj.project_name if proj else None
            item["budget_total"] = proj.contract_amount if proj else None
            if proj and proj.contract_amount and float(proj.contract_amount) > 0:
                pct = float(item.get("total_expense") or 0) / float(proj.contract_amount) * 100
                item["usage_pct"] = round(pct, 1)
                item["alert"] = "critical" if pct >= 100 else ("warning" if pct >= 80 else "normal")

        items.sort(
            key=lambda x: x["usage_pct"] if x["usage_pct"] is not None else -1,
            reverse=order_desc,
        )
        return {"items": items[:top_n], "total_projects": total}

    async def get_category_breakdown(self, year: Optional[int] = None, category: Optional[str] = None) -> dict:
        """依計畫類別 × 委託單位／協力廠商 應收付（owner 2026-09-05）"""
        return await self.repo.get_category_breakdown(year=year, category=category)

    async def get_aging_analysis(
        self,
        direction: str = "receivable",
        year: Optional[int] = None,
    ) -> dict:
        """應收/應付帳齡分析"""
        buckets = await self.repo.get_aging_analysis(direction=direction, year=year)

        result_buckets = []
        total_count = 0
        total_outstanding = Decimal("0")

        for bucket_name in ["0-30", "31-60", "61-90", "90+"]:
            b = buckets[bucket_name]
            result_buckets.append({
                "bucket": bucket_name,
                "count": b["count"],
                "amount": b["amount"],
            })
            total_count += b["count"]
            total_outstanding += b["amount"]

        return {
            "direction": direction,
            "buckets": result_buckets,
            "total_outstanding": total_outstanding,
            "total_count": total_count,
        }

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

        # 批量取完整彙總 (3 queries 取代 N*3)
        summaries = await self.repo.get_batch_project_summaries(top_case_codes)
        return [s for s in summaries if s is not None]
