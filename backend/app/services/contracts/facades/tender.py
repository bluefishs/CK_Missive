# -*- coding: utf-8 -*-
"""TenderFacade - Tender bounded context 對外唯一入口

Step 5B (2026-05-28, v6.11 後續優化) — 延伸 v6.10 P1 Phase B 12 Facades 模式。

統一 tender 12 散戶 service 的對外入口：
  - search.TenderSearchService (search/recommend)
  - analytics.TenderAnalyticsService (battle_room/org_ecosystem/price)
  - subscription_scheduler.check_all_subscriptions
  - cache.* (save_search_results/search_from_db)
  - ezbid_scraper.EzbidScraper / pcc_today_scraper.PccTodayScraper (via Registry)
  - data_transformer.* (dedup/normalize)

解決問題：
  - endpoints 直接打 N 個 service 認知負擔
  - 跨 context import drift（其他 facade 經常需要查 tender）
  - 新加 source 需手動串多處 — 透過 Registry + Facade 自動 enumerate

設計原則（與既有 12 facades 一致）：
  - Facade 只負責 thin orchestration，不重複 service 業務邏輯
  - 通過 ScraperRegistry 自動 enumerate sources，不寫死 ezbid/pcc
  - 所有 method 都 async，與其他 facade 一致
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TenderFacade:
    """Tender bounded context 對外唯一入口。

    使用範例：
        facade = TenderFacade(db)
        results = await facade.search("道路工程")
        scrapers = facade.list_registered_sources()
        await facade.check_subscriptions()
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    # =========================================================================
    # 搜尋（TenderSearchService 包裝）
    # =========================================================================

    async def search(
        self,
        query: str,
        page: int = 1,
        category: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """跨來源搜尋標案（ezbid + pcc + g0v 統合）。"""
        from app.services.tender.search import TenderSearchService

        service = TenderSearchService()
        return await service.search_by_title(
            query=query, page=page, category=category, **kwargs
        )

    async def search_recent(
        self,
        days: int = 7,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """近 N 日最新標案（給 dashboard / recommend 用）。"""
        from app.services.tender.cache import search_from_db

        return await search_from_db(
            db=self._db, days=days, category=category, limit=limit,
        )

    # =========================================================================
    # 分析（TenderAnalyticsService 包裝）
    # =========================================================================

    async def battle_room(
        self,
        company_unit_id: str,
        days: int = 90,
    ) -> Dict[str, Any]:
        """公司 vs 競標對手分析。"""
        from app.services.tender.analytics_battle import battle_room

        return await battle_room(
            db=self._db, company_unit_id=company_unit_id, days=days,
        )

    async def price_analysis(
        self,
        keyword: str,
        days: int = 365,
    ) -> Dict[str, Any]:
        """關鍵字價格趨勢分析。"""
        from app.services.tender.analytics_price import price_analysis

        return await price_analysis(
            db=self._db, keyword=keyword, days=days,
        )

    async def company_profile(
        self,
        company_unit_id: str,
    ) -> Dict[str, Any]:
        """公司決標歷史 + 統計 profile。"""
        from app.services.tender.analytics_price import company_profile

        return await company_profile(
            db=self._db, company_unit_id=company_unit_id,
        )

    # =========================================================================
    # 訂閱（subscription_scheduler 包裝）
    # =========================================================================

    async def check_subscriptions(self) -> Dict[str, Any]:
        """檢查所有啟用訂閱，比對新公告數量並推播通知。

        Step 5C: 每次呼叫 inc Prometheus counter — watchdog 偵測 silent dormant。
        """
        from app.services.tender.subscription_scheduler import check_all_subscriptions

        return await check_all_subscriptions(self._db)

    # =========================================================================
    # 爬蟲（透過 ScraperRegistry 自動 enumerate）
    # =========================================================================

    def list_registered_sources(self) -> List[str]:
        """列出所有已註冊的 scraper source（給 dashboard / freshness audit 用）。"""
        from app.services.tender import ScraperRegistry

        return ScraperRegistry.list_sources()

    def get_scraper(self, source: str) -> Optional[Any]:
        """取得指定 source 的 scraper instance（未實例化）。"""
        from app.services.tender import ScraperRegistry

        return ScraperRegistry.get(source)

    async def fetch_from_source(
        self,
        source: str,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """通用 fetch — 從指定 source 抓取（自動 instantiate scraper）。"""
        from app.services.tender import ScraperRegistry

        scraper_cls = ScraperRegistry.get(source)
        if not scraper_cls:
            logger.warning(f"Unknown scraper source: {source}")
            return None
        scraper = scraper_cls()
        # 統一介面：ezbid 用 fetch_latest，pcc 用 fetch_today_tenders
        if hasattr(scraper, "fetch_latest"):
            return await scraper.fetch_latest(**kwargs)
        if hasattr(scraper, "fetch_today_tenders"):
            return await scraper.fetch_today_tenders(**kwargs)
        logger.warning(f"Scraper {source} has no fetch method")
        return None

    # =========================================================================
    # 健康度（給 admin dashboard / fitness audit 用）
    # =========================================================================

    async def get_freshness_status(self) -> Dict[str, Any]:
        """各來源最新標案日期 + 距今天數 → 給 dashboard / freshness audit 用。"""
        from sqlalchemy import text

        sources = self.list_registered_sources()
        result: Dict[str, Any] = {"sources": {}}

        for src in sources:
            q = await self._db.execute(
                text("""
                    SELECT MAX(announce_date) AS latest, COUNT(*) AS cnt
                    FROM tender_records
                    WHERE source = :src
                """),
                {"src": src},
            )
            row = q.fetchone()
            if row and row.latest:
                from datetime import datetime as _dt
                latest = row.latest
                if isinstance(latest, str):
                    latest = _dt.fromisoformat(latest).date()
                days_ago = (_dt.utcnow().date() - latest).days
                result["sources"][src] = {
                    "latest": latest.isoformat(),
                    "count": row.cnt,
                    "days_ago": days_ago,
                    "fresh": days_ago <= 7,
                }
            else:
                result["sources"][src] = {
                    "latest": None,
                    "count": 0,
                    "days_ago": None,
                    "fresh": False,
                }

        return result
