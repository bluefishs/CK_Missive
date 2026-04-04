"""
標案分析服務 (Tender Analytics)

提供招標儀表板、投標戰情室、機關生態分析、廠商分析、底價分析等功能。
基於 pcc-api.openfun.app 開放資料 + Redis 快取。

Version: 1.0.0
"""
import logging
from typing import Optional, List, Dict, Any
from collections import Counter, defaultdict

from app.services.tender_search_service import TenderSearchService

logger = logging.getLogger(__name__)


class TenderAnalyticsService:
    """標案分析引擎"""

    def __init__(self):
        self.search = TenderSearchService()

    # =========================================================================
    # 1. 招標採購儀表板
    # =========================================================================

    async def dashboard(self, keywords: Optional[List[str]] = None) -> dict:
        """招標採購儀表板 — 近期統計 + 類別分布 + 推薦標案

        Args:
            keywords: 監控關鍵字 (預設使用乾坤業務關鍵字)
        """
        from app.services.tender_search_service import CK_BUSINESS_KEYWORDS
        kw_list = keywords or CK_BUSINESS_KEYWORDS[:5]

        # 推薦標案
        recommend = await self.search.recommend_tenders(keywords=kw_list)
        records = recommend.get("records", [])

        # 統計
        category_counter: Counter = Counter()
        type_counter: Counter = Counter()
        agency_counter: Counter = Counter()

        for r in records:
            category_counter[r.get("category", "未分類")] += 1
            type_counter[r.get("type", "未分類")] += 1
            agency_counter[r.get("unit_name", "未知")] += 1

        return {
            "total_found": recommend.get("total", 0),
            "keywords_used": kw_list,
            "recent_tenders": records[:10],
            "category_distribution": [
                {"name": k, "value": v} for k, v in category_counter.most_common(10)
            ],
            "type_distribution": [
                {"name": k, "value": v} for k, v in type_counter.most_common(10)
            ],
            "top_agencies": [
                {"name": k, "count": v} for k, v in agency_counter.most_common(10)
            ],
        }

    # =========================================================================
    # 2. 投標戰情室 — 相似標案 + 競爭對手
    # =========================================================================

    async def battle_room(
        self,
        unit_id: str,
        job_number: str,
    ) -> dict:
        """投標戰情室 — 針對特定標案的競爭分析

        Args:
            unit_id: 機關代碼
            job_number: 標案案號
        """
        # 取得標案詳情
        detail = await self.search.get_tender_detail(unit_id, job_number)
        if not detail:
            return {"error": "標案不存在"}

        title = detail.get("title", "")
        latest = detail.get("latest", {})
        agency = latest.get("agency_name", "")

        # 相似標案 (用標題前 10 字搜尋)
        search_key = title[:10] if len(title) > 10 else title
        similar = await self.search.search_by_title(query=search_key, page=1)
        similar_records = similar.get("records", [])[:10]

        # 排除自己
        similar_records = [
            r for r in similar_records
            if r.get("job_number") != job_number
        ]

        # 從相似標案中提取所有競爭廠商
        competitor_counter: Counter = Counter()
        competitor_wins: Counter = Counter()

        for r in similar_records:
            winners = r.get("winner_names", [])
            bidders = r.get("bidder_names", [])
            for w in winners:
                competitor_counter[w] += 1
                competitor_wins[w] += 1
            for b in bidders:
                competitor_counter[b] += 1

        # 競爭對手排行
        competitors = []
        for name, total in competitor_counter.most_common(15):
            wins = competitor_wins.get(name, 0)
            competitors.append({
                "name": name,
                "appear_count": total,
                "win_count": wins,
                "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
            })

        return {
            "tender": {
                "title": title,
                "unit_id": unit_id,
                "job_number": job_number,
                "agency": agency,
                "budget": latest.get("budget"),
                "method": latest.get("method"),
                "deadline": latest.get("deadline"),
                "status": latest.get("status"),
            },
            "similar_tenders": similar_records[:8],
            "similar_count": len(similar_records),
            "competitors": competitors,
            "competitor_count": len(competitors),
        }

    # =========================================================================
    # 3. 機關生態分析
    # =========================================================================

    async def org_ecosystem(
        self,
        org_name: str,
        pages: int = 3,
    ) -> dict:
        """機關生態分析 — 某機關的歷年標案 + 得標廠商分布

        Args:
            org_name: 機關名稱
            pages: 搜尋頁數 (每頁約 100 筆)
        """
        all_records: list = []

        for page in range(1, pages + 1):
            result = await self.search.search_by_title(
                query=org_name, page=page,
            )
            records = result.get("records", [])
            if not records:
                break
            all_records.extend(records)

        if not all_records:
            return {"org_name": org_name, "total": 0, "records": []}

        # 統計
        year_counter: Counter = Counter()
        category_counter: Counter = Counter()
        winner_counter: Counter = Counter()
        type_counter: Counter = Counter()
        total_budget = 0
        budget_count = 0

        for r in all_records:
            # 年度
            raw_date = r.get("raw_date") or r.get("date", "")
            year = str(raw_date)[:4] if raw_date else "未知"
            year_counter[year] += 1

            category_counter[r.get("category", "未分類")] += 1
            type_counter[r.get("type", "未分類")] += 1

            for w in r.get("winner_names", []):
                winner_counter[w] += 1

        return {
            "org_name": org_name,
            "total": len(all_records),
            "year_trend": [
                {"year": k, "count": v}
                for k, v in sorted(year_counter.items())
            ],
            "category_distribution": [
                {"name": k, "value": v}
                for k, v in category_counter.most_common(10)
            ],
            "type_distribution": [
                {"name": k, "value": v}
                for k, v in type_counter.most_common(10)
            ],
            "top_winners": [
                {"name": k, "count": v}
                for k, v in winner_counter.most_common(20)
            ],
            "recent_tenders": all_records[:10],
        }

    # =========================================================================
    # 4. 廠商分析 (潛在對手/自家)
    # =========================================================================

    async def company_profile(
        self,
        company_name: str,
        pages: int = 3,
    ) -> dict:
        """廠商得標分析 — 某廠商的歷年得標 + 機關分布 + 類別分布

        Args:
            company_name: 廠商名稱
            pages: 搜尋頁數
        """
        all_records: list = []

        for page in range(1, pages + 1):
            result = await self.search.search_by_company(
                company_name=company_name, page=page,
            )
            records = result.get("records", [])
            if not records:
                break
            all_records.extend(records)

        if not all_records:
            return {"company_name": company_name, "total": 0}

        # 分析
        year_counter: Counter = Counter()
        agency_counter: Counter = Counter()
        category_counter: Counter = Counter()
        won_count = 0

        for r in all_records:
            raw_date = r.get("raw_date") or r.get("date", "")
            year = str(raw_date)[:4] if raw_date else "未知"
            year_counter[year] += 1
            agency_counter[r.get("unit_name", "未知")] += 1
            category_counter[r.get("category", "未分類")] += 1
            if company_name in (r.get("winner_names") or []):
                won_count += 1

        return {
            "company_name": company_name,
            "total": len(all_records),
            "won_count": won_count,
            "win_rate": round(won_count / len(all_records) * 100, 1) if all_records else 0,
            "year_trend": [
                {"year": k, "count": v}
                for k, v in sorted(year_counter.items())
            ],
            "top_agencies": [
                {"name": k, "count": v}
                for k, v in agency_counter.most_common(15)
            ],
            "category_distribution": [
                {"name": k, "value": v}
                for k, v in category_counter.most_common(10)
            ],
            "recent_tenders": all_records[:10],
        }
