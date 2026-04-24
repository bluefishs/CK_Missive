"""Regression test (2026-04-24):
ezbid_scraper._get_cache / _set_cache must await redis calls (async API).

Prior bug: methods used sync `self._redis.get(key)` calling an async
Redis client would return coroutine, caught by try/except → silent cache
miss on every request → 3.5s cold hit on every tender search.
"""
import inspect

from app.services.ezbid_scraper import EzbidScraper


def test_get_cache_uses_await():
    src = inspect.getsource(EzbidScraper._get_cache)
    assert "await redis.get" in src or "await self._redis.get" in src, (
        "_get_cache must await redis.get(key), sync call on async client "
        "leaks coroutines and cache always misses"
    )


def test_set_cache_uses_await():
    src = inspect.getsource(EzbidScraper._set_cache)
    assert "await redis.set" in src or "await self._redis.set" in src, (
        "_set_cache must await redis.set(...)"
    )


def test_get_cache_falls_back_to_global_redis():
    """When scraper is instantiated without redis_client, _get_cache
    should fetch global redis via get_redis()."""
    src = inspect.getsource(EzbidScraper._get_cache)
    assert "get_redis" in src, (
        "_get_cache must fallback to global redis when self._redis is None"
    )
