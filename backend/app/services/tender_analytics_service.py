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
        """招標採購儀表板 — 多區塊分類統計 + 最新標案列表

        回傳:
        - 統計卡片: 招標/決標/無法決標 筆數
        - 分類列表: 本週招標/決標/得標廠商/無法決標/公開徵求
        - 類別分布圖表
        """
        from datetime import datetime, timedelta
        from app.services.tender_search_service import CK_BUSINESS_KEYWORDS
        kw_list = keywords or CK_BUSINESS_KEYWORDS[:5]

        import asyncio
        all_records = []
        seen_keys = set()

        # === 主要來源: ezbid 今日全量 (統一服務層, 快取共享) ===
        # dashboard / recommend / search 共用 get_today_all() 避免重複爬取
        try:
            from app.services.ezbid_scraper import EzbidScraper
            scraper = EzbidScraper()
            primary_result = await scraper.get_today_all()
            for r in primary_result.get("records", []):
                key = f"ezbid-{r.get('ezbid_id', '')}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_records.append({
                        "date": r.get("date", ""),
                        "raw_date": int(r.get("date", "0").replace("-", "")) if r.get("date") else 0,
                        "title": r.get("title", ""),
                        "type": r.get("type", ""),
                        "category": r.get("category", ""),
                        "unit_id": r.get("ezbid_id", ""),
                        "unit_name": r.get("unit_name", ""),
                        "job_number": "",
                        "winner_names": [],
                        "source": "ezbid",
                        "budget": r.get("budget"),
                        "days_left": r.get("days_left"),
                        "ezbid_url": r.get("ezbid_url", ""),
                    })
            logger.info("ezbid today (shared cache): %d records", len(primary_result.get("records", [])))
        except Exception as e:
            logger.warning(f"ezbid today fetch failed: {e}")

        # === 補充來源 0: PCC 官網今日全量 (1900+ 筆, 含招標+決標+選擇性) ===
        try:
            from app.services.pcc_today_scraper import PccTodayScraper
            pcc_scraper = PccTodayScraper()
            pcc_result = await pcc_scraper.fetch_today_tenders()
            for r in pcc_result.get("records", []):
                key = f"pcc-{r.get('unit_id', '')}-{r.get('job_number', '')}"
                if key and key != "pcc--" and key not in seen_keys:
                    seen_keys.add(key)
                    all_records.append(r)
            logger.info(
                "PCC today (verify=False): %d records, types=%s",
                len(pcc_result.get("records", [])),
                pcc_result.get("by_type", {}),
            )
        except Exception as e:
            logger.debug(f"PCC today scrape skipped: {e}")

        # === 補充來源 1: g0v PCC API 關鍵字搜尋 (含決標資料) ===
        # 擴大搜尋: 5 關鍵字 × 5 頁 + 通用詞 3 頁 → 涵蓋更多決標公告
        async def fetch_kw(kw, page):
            return kw, await self.search.search_by_title(kw, page=page)

        # 業務關鍵字 5 頁 + 通用決標關鍵字 3 頁
        general_kws = ["工程", "勞務", "財物"]
        tasks = [fetch_kw(kw, p) for kw in kw_list[:5] for p in range(1, 6)]
        tasks += [fetch_kw(kw, p) for kw in general_kws for p in range(1, 4)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, Exception):
                continue
            kw, result = item
            for r in result.get("records", []):
                key = f"{r['unit_id']}-{r['job_number']}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    r["matched_keyword"] = kw
                    all_records.append(r)

        # === 補充來源 2: ezbid 關鍵字搜尋 (業務相關標案精準匹配) ===
        try:
            ezbid_kw_result = await scraper.fetch_for_keywords(kw_list[:5])
            if not isinstance(ezbid_kw_result, Exception):
                for r in ezbid_kw_result.get("records", []):
                    key = f"ezbid-{r.get('ezbid_id', '')}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_records.append({
                            "date": r.get("date", ""),
                            "raw_date": int(r.get("date", "0").replace("-", "")) if r.get("date") else 0,
                            "title": r.get("title", ""),
                            "type": r.get("type", ""),
                            "category": r.get("category", ""),
                            "unit_id": r.get("ezbid_id", ""),
                            "unit_name": r.get("unit_name", ""),
                            "job_number": "",
                            "winner_names": [],
                            "matched_keyword": r.get("matched_keyword"),
                            "source": "ezbid",
                            "budget": r.get("budget"),
                        })
        except Exception as e:
            logger.debug(f"ezbid keyword supplement failed: {e}")

        # 按日期排序
        all_records.sort(key=lambda r: r.get("raw_date", 0), reverse=True)

        # 日期判斷 — 使用資料中的最新日期 (含 ezbid 即時資料)
        all_dates = sorted(set(r.get("date", "") for r in all_records if r.get("date")), reverse=True)
        latest_date = all_dates[0] if all_dates else datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # 按類型分類 (精確匹配, 排除更正公告和非招標)
        def is_bid(r):
            """招標公告 (排除更正、決標、公開取得)"""
            t = r.get("type", "")
            return ("招標" in t and "更正" not in t and "決標" not in t
                    and "公開取得" not in t)

        def is_award(r):
            """決標公告"""
            return "決標" in r.get("type", "") and "無法" not in r.get("type", "")

        def is_failed(r):
            return "無法決標" in r.get("type", "")

        def is_rfp(r):
            """公開取得報價單/企劃書"""
            return "公開取得" in r.get("type", "") and "更正" not in r.get("type", "")

        # 最新招標：使用整體最新日期
        # 統計卡片以 PCC 精確分類為準 (ezbid type 全為 '公開招標公告'，不精確)
        # 列表顯示仍包含 ezbid 記錄
        latest_bid = [r for r in all_records if r.get("date") == latest_date and is_bid(r)]
        latest_bid_pcc_count = sum(1 for r in latest_bid if r.get("source") == "pcc")

        # 最新決標：使用 PCC 最新日期 (ezbid 不提供決標資料)
        pcc_dates = sorted(set(r.get("date", "") for r in all_records if r.get("date") and r.get("source") != "ezbid"), reverse=True)
        pcc_latest = pcc_dates[0] if pcc_dates else latest_date
        latest_award = [r for r in all_records if r.get("date") == pcc_latest and is_award(r)]
        week_new_bid = [r for r in all_records if r.get("date", "") >= week_ago and is_bid(r)]
        week_new_award = [r for r in all_records if r.get("date", "") >= week_ago and is_award(r)]
        recent_failed = [r for r in all_records if is_failed(r)]
        recent_rfp = [r for r in all_records if is_rfp(r)]

        # 得標廠商統計
        winner_counter: Counter = Counter()
        for r in all_records:
            for w in r.get("winner_names", []):
                if w:
                    winner_counter[w] += 1

        # 經費規模分布
        budget_ranges = Counter()
        for r in all_records:
            b = r.get("budget")
            if not b:
                continue
            try:
                amount = int(b) if isinstance(b, (int, float)) else int(str(b).replace(",", ""))
            except (ValueError, TypeError):
                continue
            if amount < 500_000:
                budget_ranges["50萬以下"] += 1
            elif amount < 1_000_000:
                budget_ranges["50~100萬"] += 1
            elif amount < 5_000_000:
                budget_ranges["100~500萬"] += 1
            elif amount < 10_000_000:
                budget_ranges["500~1000萬"] += 1
            elif amount < 50_000_000:
                budget_ranges["1000萬~5000萬"] += 1
            else:
                budget_ranges["5000萬以上"] += 1

        # 類別/機關統計
        category_counter: Counter = Counter()
        type_counter: Counter = Counter()
        agency_counter: Counter = Counter()
        for r in all_records:
            category_counter[r.get("category", "未分類")] += 1
            t = r.get("type", "")
            if "招標" in t:
                type_counter["招標公告"] += 1
            elif "無法決標" in t:
                type_counter["無法決標"] += 1
            elif "決標" in t:
                type_counter["決標公告"] += 1
            elif "取得報價" in t:
                type_counter["公開取得報價"] += 1
            else:
                type_counter[t[:10] if t else "其他"] += 1
            agency_counter[r.get("unit_name", "未知")] += 1

        def slim(r):
            return {
                "title": r.get("title", "")[:80],
                "date": r.get("date", ""),
                "type": r.get("type", "")[:20],
                "category": r.get("category", ""),
                "unit_name": r.get("unit_name", ""),
                "unit_id": r.get("unit_id", ""),
                "job_number": r.get("job_number", ""),
                "winner_names": r.get("winner_names", [])[:3],
                "matched_keyword": r.get("matched_keyword"),
                "source": r.get("source", "pcc"),
                "budget": r.get("budget"),
            }

        ezbid_count = sum(1 for r in all_records if r.get("source") == "ezbid")
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 計算各列表的實際日期範圍
        def date_range(records):
            dates = sorted(set(r.get("date", "") for r in records if r.get("date")))
            if not dates:
                return ""
            if len(dates) == 1:
                return dates[0][5:]  # MM-DD
            return f"{dates[0][5:]}~{dates[-1][5:]}"

        return {
            "total_found": len(all_records),
            "keywords_used": kw_list,
            "latest_date": latest_date,
            "today_date": today_str,
            "ezbid_count": ezbid_count,
            # 各區塊實際日期範圍
            "date_ranges": {
                "latest_bid": date_range(latest_bid),
                "latest_award": date_range(latest_award),
                "week_bid": date_range(week_new_bid),
                "week_award": date_range(week_new_award),
                "failed": date_range(recent_failed),
                "rfp": date_range(recent_rfp),
            },
            # 統計卡片 (PCC 精確分類為主)
            "stats": {
                "latest_bid": latest_bid_pcc_count or len(latest_bid),
                "latest_award": len(latest_award),
                "week_new_bid": len(week_new_bid),
                "week_new_award": len(week_new_award),
                "failed_award": len(recent_failed),
                "rfp_count": len(recent_rfp),
            },
            # 列表區塊
            "latest_bid_list": [slim(r) for r in latest_bid[:50]],
            "latest_award_list": [slim(r) for r in latest_award[:50]],
            "week_new_bid_list": [slim(r) for r in week_new_bid[:50]],
            "week_new_award_list": [slim(r) for r in week_new_award[:50]],
            "failed_award_list": [slim(r) for r in recent_failed[:30]],
            "rfp_list": [slim(r) for r in recent_rfp[:30]],
            "top_winners": [
                {"name": k, "count": v} for k, v in winner_counter.most_common(10)
            ],
            # 圖表
            "category_distribution": [
                {"name": k, "value": v} for k, v in category_counter.most_common(10)
            ],
            "type_distribution": [
                {"name": k, "value": v} for k, v in type_counter.most_common(10)
            ],
            "top_agencies": [
                {"name": k, "count": v} for k, v in agency_counter.most_common(10)
            ],
            "budget_distribution": [
                {"name": k, "value": v} for k, v in budget_ranges.most_common()
            ],
        }

    # =========================================================================
    # 委派方法 — 拆分至子模組
    # =========================================================================

    async def battle_room(self, unit_id: str, job_number: str) -> dict:
        """投標戰情室 — 委派至 tender_analytics_battle"""
        from app.services.tender_analytics_battle import battle_room
        return await battle_room(self.search, unit_id, job_number)

    async def org_ecosystem(self, org_name: str, pages: int = 10) -> dict:
        """機關生態分析 — 委派至 tender_analytics_battle"""
        from app.services.tender_analytics_battle import org_ecosystem
        return await org_ecosystem(self.search, org_name, pages)

    async def price_analysis(self, unit_id: str, job_number: str) -> dict:
        """底價分析 — 委派至 tender_analytics_price"""
        from app.services.tender_analytics_price import price_analysis
        return await price_analysis(self.search, unit_id, job_number)

    async def price_trends(self, query: str, pages: int = 3) -> dict:
        """價格趨勢 — 委派至 tender_analytics_price"""
        from app.services.tender_analytics_price import price_trends
        return await price_trends(self.search, query, pages)

    async def company_profile(self, company_name: str, pages: int = 3) -> dict:
        """廠商分析 — 委派至 tender_analytics_price"""
        from app.services.tender_analytics_price import company_profile
        return await company_profile(self.search, company_name, pages)
