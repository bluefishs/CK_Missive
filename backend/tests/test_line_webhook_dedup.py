# -*- coding: utf-8 -*-
"""LINE 去重走 redis、redis 不在時退回行程內（A117，2026-09-08）。"""
import pytest
from app.api.endpoints import line_webhook as lw


class _FakeRedis:
    def __init__(self): self.keys = set()
    async def set(self, k, v, nx=False, ex=None):
        if nx and k in self.keys: return None
        self.keys.add(k); return True


@pytest.mark.asyncio
async def test_redis_path_dedups(monkeypatch):
    fake = _FakeRedis()
    async def _get(): return fake
    monkeypatch.setattr("app.core.redis_client.get_redis", _get)
    assert await lw._is_duplicate_event("m1") is False
    assert await lw._is_duplicate_event("m1") is True
    assert await lw._is_duplicate_event("m2") is False


@pytest.mark.asyncio
async def test_fallback_when_redis_missing(monkeypatch):
    async def _get(): return None
    monkeypatch.setattr("app.core.redis_client.get_redis", _get)
    lw._DEDUP_CACHE.clear()
    assert await lw._is_duplicate_event("x1") is False
    assert await lw._is_duplicate_event("x1") is True
