"""Tender bounded context (DDD Wave 4, 2026-04-28).

Houses 標案檢索 (Public Procurement) — search/cache/scrapers/analytics/subscription.

Public API (use specific submodule for sub-types):
    .search              — TenderSearchService / CK_BUSINESS_KEYWORDS
    .search_query        — build_tender_search_sql / rerank_by_title_similarity
    .data_transformer    — dedup_records / normalize_record / extract_award_details
    .cache               — _ingest_tender_entities / save_search_results / search_from_db
    .subscription_scheduler — check_all_subscriptions
    .analytics           — TenderAnalyticsService (Facade)
    .analytics_battle    — battle_room / org_ecosystem
    .analytics_price     — price_analysis / price_trends / company_profile
    .ezbid_scraper       — EzbidScraper
    .pcc_today_scraper   — PccTodayScraper
"""
from .search import TenderSearchService  # noqa: F401
from .analytics import TenderAnalyticsService  # noqa: F401
from .ezbid_scraper import EzbidScraper  # noqa: F401
from .pcc_today_scraper import PccTodayScraper  # noqa: F401
# Step 5A (2026-05-28): scraper base + registry — 統一 abstract base
from .scraper_base import (  # noqa: F401
    TenderScraperBase,
    ScraperRegistry,
    register_scraper,
)
