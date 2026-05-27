"""TenderFacade tests (Step 5B, 2026-05-28).

驗證 v6.10 P1 13 facade（TenderFacade 加入後）：
- 介面完整性 — 所有預期 method 存在
- ScraperRegistry 整合 — list/get/fetch 自動 enumerate
- import 不破壞 既有 12 facades
"""
import inspect

import pytest


def test_tender_facade_importable():
    """TenderFacade 必須能從 contracts.facades 匯入。"""
    from app.services.contracts.facades import TenderFacade
    assert TenderFacade is not None


def test_tender_facade_has_required_methods():
    """確保 facade 對外介面完整 — search/analytics/subscription/scraper."""
    from app.services.contracts.facades import TenderFacade

    expected_methods = [
        "search",
        "search_recent",
        "battle_room",
        "price_analysis",
        "company_profile",
        "check_subscriptions",
        "list_registered_sources",
        "get_scraper",
        "fetch_from_source",
        "get_freshness_status",
    ]

    for m in expected_methods:
        assert hasattr(TenderFacade, m), f"TenderFacade missing method: {m}"
        method = getattr(TenderFacade, m)
        assert callable(method), f"TenderFacade.{m} not callable"


def test_tender_facade_methods_are_async():
    """除了 list_registered_sources / get_scraper 同步外，其餘必須 async（與其他 facade 一致）。"""
    from app.services.contracts.facades import TenderFacade

    sync_methods = {"list_registered_sources", "get_scraper"}
    for m in dir(TenderFacade):
        if m.startswith("_"):
            continue
        method = getattr(TenderFacade, m)
        if not callable(method):
            continue
        if m in sync_methods:
            continue
        assert inspect.iscoroutinefunction(method), (
            f"TenderFacade.{m} must be async (與其他 facade 一致)"
        )


def test_facade_uses_scraper_registry():
    """list_registered_sources 必須返回 ezbid + pcc（從 Registry）。"""
    from app.services.contracts.facades import TenderFacade
    # 觸發 scraper import + registration
    from app.services.tender.ezbid_scraper import EzbidScraper  # noqa
    from app.services.tender.pcc_today_scraper import PccTodayScraper  # noqa

    # Mock db
    facade = TenderFacade(db=None)  # type: ignore
    sources = facade.list_registered_sources()
    assert "ezbid" in sources
    assert "pcc" in sources


def test_facades_init_exports_13():
    """v6.11 後 facades 應為 13（v6.10 12 + TenderFacade）。"""
    from app.services.contracts import facades

    assert "TenderFacade" in facades.__all__
    assert len(facades.__all__) == 13


def test_get_scraper_returns_class():
    from app.services.contracts.facades import TenderFacade
    from app.services.tender import EzbidScraper

    facade = TenderFacade(db=None)  # type: ignore
    assert facade.get_scraper("ezbid") is EzbidScraper
    assert facade.get_scraper("nonexistent") is None
