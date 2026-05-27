"""Tender Scraper Registry tests (Step 5A, 2026-05-28).

Validate ScraperRegistry auto-enumeration of @register_scraper decorated scrapers.
給 subscription_scheduler / freshness audit / Grafana dashboard 自動發現新 scraper。
"""
import pytest


def test_registry_lists_ezbid_and_pcc():
    """Import 既有 scraper 後 registry 應自動列出 ezbid + pcc。"""
    # Trigger registration via import
    from app.services.tender.ezbid_scraper import EzbidScraper  # noqa: F401
    from app.services.tender.pcc_today_scraper import PccTodayScraper  # noqa: F401
    from app.services.tender import ScraperRegistry

    sources = ScraperRegistry.list_sources()
    assert "ezbid" in sources, f"ezbid 未註冊 (got {sources})"
    assert "pcc" in sources, f"pcc 未註冊 (got {sources})"


def test_registry_get_returns_class():
    from app.services.tender import ScraperRegistry, EzbidScraper, PccTodayScraper

    assert ScraperRegistry.get("ezbid") is EzbidScraper
    assert ScraperRegistry.get("pcc") is PccTodayScraper
    assert ScraperRegistry.get("nonexistent") is None


def test_registry_get_all_returns_dict():
    from app.services.tender import ScraperRegistry

    all_scrapers = ScraperRegistry.get_all()
    assert isinstance(all_scrapers, dict)
    assert "ezbid" in all_scrapers
    assert "pcc" in all_scrapers


def test_scrapers_have_source_name_attr():
    """每個 registered scraper 必須有 source_name class attr — 給 ScraperRegistry 列出。"""
    from app.services.tender import EzbidScraper, PccTodayScraper

    assert EzbidScraper.source_name == "ezbid"
    assert PccTodayScraper.source_name == "pcc"


def test_register_scraper_decorator_can_override():
    """同名重複註冊應 log warning 但允許（測試/熱載入場景）。"""
    from app.services.tender.scraper_base import register_scraper, ScraperRegistry

    @register_scraper("test_dummy_source")
    class DummyA:
        source_name = "test_dummy_source"

    @register_scraper("test_dummy_source")
    class DummyB:
        source_name = "test_dummy_source"

    # 後註冊覆蓋先註冊
    assert ScraperRegistry.get("test_dummy_source") is DummyB

    # Cleanup
    from app.services.tender.scraper_base import _REGISTRY
    _REGISTRY.pop("test_dummy_source", None)
