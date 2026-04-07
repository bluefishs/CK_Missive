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

    # =========================================================================
    # 5. 底價分析 — 單一標案
    # =========================================================================

    async def price_analysis(
        self,
        unit_id: str,
        job_number: str,
    ) -> dict:
        """單一標案底價分析 — budget vs floor vs award

        Args:
            unit_id: 機關代碼
            job_number: 標案案號

        Returns:
            包含預算、底價、決標金額及差異百分比的結構化分析
        """
        detail = await self.search.get_tender_detail(unit_id, job_number)
        if not detail:
            return {"error": "標案不存在", "unit_id": unit_id, "job_number": job_number}

        title = detail.get("title", "")
        events = detail.get("events", [])

        # 從所有事件中提取最完整的價格資料
        budget = None
        floor_price = None
        award_amount = None
        award_date = None
        award_items: list = []

        for event in events:
            event_detail = event.get("detail", {})
            award_detail = event.get("award_details", {})

            # 預算金額 (從 detail.budget 解析)
            if budget is None and event_detail.get("budget"):
                budget = self._safe_parse_amount(event_detail["budget"])

            # 底價 (從 award_details)
            if floor_price is None and award_detail.get("floor_price") is not None:
                floor_price = award_detail["floor_price"]

            # 決標金額
            if award_amount is None and award_detail.get("total_award_amount") is not None:
                award_amount = award_detail["total_award_amount"]

            # 決標日期
            if award_date is None and award_detail.get("award_date"):
                award_date = award_detail["award_date"]

            # 品項明細 (取最完整的)
            items = award_detail.get("award_items", [])
            if items and len(items) > len(award_items):
                award_items = items

        # 計算差異百分比
        budget_award_variance = None
        floor_award_variance = None
        budget_floor_variance = None
        savings_rate = None

        if budget and award_amount:
            budget_award_variance = round((award_amount - budget) / budget * 100, 2)

        if floor_price and award_amount:
            floor_award_variance = round((award_amount - floor_price) / floor_price * 100, 2)

        if budget and floor_price:
            budget_floor_variance = round((floor_price - budget) / budget * 100, 2)
            savings_rate = round((budget - floor_price) / budget * 100, 2)

        return {
            "tender": {
                "title": title,
                "unit_id": unit_id,
                "job_number": job_number,
                "unit_name": detail.get("unit_name", ""),
            },
            "prices": {
                "budget": budget,
                "floor_price": floor_price,
                "award_amount": award_amount,
                "award_date": award_date,
            },
            "analysis": {
                "budget_award_variance_pct": budget_award_variance,
                "floor_award_variance_pct": floor_award_variance,
                "budget_floor_variance_pct": budget_floor_variance,
                "savings_rate_pct": savings_rate,
            },
            "award_items": award_items,
        }

    # =========================================================================
    # 6. 價格趨勢 — 同類標案
    # =========================================================================

    async def price_trends(
        self,
        query: str,
        pages: int = 3,
    ) -> dict:
        """同類標案價格趨勢 — 多筆標案的價格統計

        Args:
            query: 搜尋關鍵字
            pages: 搜尋頁數

        Returns:
            包含價格統計、分布、趨勢資料
        """
        all_records: list = []
        for page in range(1, pages + 1):
            result = await self.search.search_by_title(query=query, page=page)
            records = result.get("records", [])
            if not records:
                break
            all_records.extend(records)

        if not all_records:
            return {"query": query, "total": 0, "samples": 0, "stats": {}}

        # 嘗試取得每筆標案的價格資料
        price_entries: list = []
        for r in all_records[:30]:  # 限制最多 30 筆避免過多 API 呼叫
            unit_id = r.get("unit_id", "")
            jn = r.get("job_number", "")
            if not unit_id or not jn:
                continue

            try:
                detail = await self.search.get_tender_detail(unit_id, jn)
                if not detail:
                    continue

                events = detail.get("events", [])
                budget = None
                floor_price = None
                award_amount = None

                for event in events:
                    ed = event.get("detail", {})
                    ad = event.get("award_details", {})

                    if budget is None and ed.get("budget"):
                        budget = self._safe_parse_amount(ed["budget"])
                    if floor_price is None and ad.get("floor_price") is not None:
                        floor_price = ad["floor_price"]
                    if award_amount is None and ad.get("total_award_amount") is not None:
                        award_amount = ad["total_award_amount"]

                # 至少要有一個價格欄位才計入
                if budget or floor_price or award_amount:
                    price_entries.append({
                        "title": r.get("title", "")[:60],
                        "date": r.get("date", ""),
                        "unit_name": r.get("unit_name", ""),
                        "budget": budget,
                        "floor_price": floor_price,
                        "award_amount": award_amount,
                    })
            except Exception as e:
                logger.warning(f"price_trends detail fetch failed for {jn}: {e}")
                continue

        if not price_entries:
            return {"query": query, "total": len(all_records), "samples": 0, "stats": {}}

        # 統計彙整
        budgets = [e["budget"] for e in price_entries if e["budget"] is not None]
        floors = [e["floor_price"] for e in price_entries if e["floor_price"] is not None]
        awards = [e["award_amount"] for e in price_entries if e["award_amount"] is not None]

        def _agg(values: list) -> dict:
            if not values:
                return {"count": 0, "min": None, "max": None, "avg": None, "median": None}
            sorted_v = sorted(values)
            n = len(sorted_v)
            median = sorted_v[n // 2] if n % 2 == 1 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2
            return {
                "count": n,
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(sum(values) / n, 2),
                "median": round(median, 2),
            }

        # 計算決標率 (有決標金額 / 有預算)
        award_rate = None
        if budgets and awards:
            award_rate = round(len(awards) / len(budgets) * 100, 1)

        # 價格帶分布 (以百萬為單位)
        distribution = defaultdict(int)
        for a in awards:
            bracket = int(a // 1_000_000) * 1_000_000
            label = f"{bracket // 10000}萬~{(bracket + 1_000_000) // 10000}萬"
            distribution[label] += 1

        return {
            "query": query,
            "total": len(all_records),
            "samples": len(price_entries),
            "stats": {
                "budget": _agg(budgets),
                "floor_price": _agg(floors),
                "award_amount": _agg(awards),
                "award_rate_pct": award_rate,
            },
            "distribution": [
                {"range": k, "count": v}
                for k, v in sorted(distribution.items())
            ],
            "entries": price_entries[:20],
        }

    @staticmethod
    def _safe_parse_amount(raw) -> float | None:
        """安全解析金額字串"""
        if raw is None:
            return None
        try:
            import re
            cleaned = re.sub(r'[^\d.]', '', str(raw).replace(',', ''))
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    # =========================================================================
    # 4. 廠商分析 (潛在對手/自家) [original section 4 renumbered]
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
            # 模糊匹配得標廠商 — "乾坤測繪" 匹配 "乾坤測繪科技有限公司"
            winners = r.get("winner_names") or []
            is_won = any(
                company_name in w or w in company_name
                for w in winners
            )
            if is_won:
                won_count += 1
                r["_is_won"] = True

        # recent_tenders 加入得標結果資訊
        recent = []
        for r in all_records[:20]:
            recent.append({
                "title": r.get("title", ""),
                "date": r.get("date", ""),
                "unit_name": r.get("unit_name", ""),
                "unit_id": r.get("unit_id", ""),
                "job_number": r.get("job_number", ""),
                "type": r.get("type", ""),
                "category": r.get("category", ""),
                "winner_names": r.get("winner_names", []),
                "bidder_names": r.get("bidder_names", []),
                "is_won": r.get("_is_won", False),
            })

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
            "recent_tenders": recent,
        }
