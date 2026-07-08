"""LINE 主題合併 regression（2026-07-07 落地，owner 06-30 決議）

鎖定三件事：
1. digest buffer queue/drain roundtrip（Redis 不可用 → in-memory fallback 仍運作）
2. build_digest_tail 依主題分組、空清單回空、總長 cap（防爆 LINE 5000 字限）
3. 月度軟上限：計數超過 cap → push 被拒（不打 LINE API）；Redis 掛 → fail-open
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.services.integration import line_digest_buffer as buf


@pytest.fixture(autouse=True)
def _clean_memory_buffer():
    buf._memory_buffer.clear()
    yield
    buf._memory_buffer.clear()


@pytest.mark.asyncio
async def test_queue_drain_roundtrip_memory_fallback():
    """Redis 不可用 → in-memory fallback；drain 取走並清空。"""
    with patch("app.core.redis_client.get_redis", new=AsyncMock(return_value=None)):
        assert await buf.queue_digest("🚨 吹哨者", "告警 3 筆")
        assert await buf.queue_digest("🌙 坤哥自省", "今日對話 5 筆")
        items = await buf.drain_digest()
    assert [i["topic"] for i in items] == ["🚨 吹哨者", "🌙 坤哥自省"]
    # 二次 drain 應為空（已取走）
    with patch("app.core.redis_client.get_redis", new=AsyncMock(return_value=None)):
        assert await buf.drain_digest() == []


@pytest.mark.asyncio
async def test_queue_skips_empty_text():
    with patch("app.core.redis_client.get_redis", new=AsyncMock(return_value=None)):
        assert not await buf.queue_digest("x", "   ")
    assert buf._memory_buffer == []


def test_build_digest_tail_groups_by_topic():
    items = [
        {"topic": "🚨 吹哨者", "text": "告警 3 筆", "ts": "07-07 00:30"},
        {"topic": "📋 標案訂閱", "text": "「測量」新增 2 筆", "ts": "07-07 09:00"},
        {"topic": "🚨 吹哨者", "text": "又 1 筆", "ts": "07-07 12:00"},
    ]
    tail = buf.build_digest_tail(items)
    assert "昨日主題摘要" in tail
    assert tail.index("🚨 吹哨者") < tail.index("📋 標案訂閱")  # 依首見順序
    assert tail.count("🚨 吹哨者") == 1  # 同主題只出一次標頭
    assert "告警 3 筆" in tail and "又 1 筆" in tail


def test_build_digest_tail_empty_and_cap():
    assert buf.build_digest_tail([]) == ""
    items = [{"topic": "T", "text": "x" * 500, "ts": ""} for _ in range(10)]
    tail = buf.build_digest_tail(items)
    assert len(tail) <= buf.DIGEST_TAIL_MAX_CHARS
    assert "其餘見系統內通知" in tail


# ────────── 月度軟上限 ──────────

class _FakeRedis:
    def __init__(self, start: int):
        self.n = start

    async def incr(self, _key):
        self.n += 1
        return self.n

    async def expire(self, _key, _ttl):
        return True


@pytest.mark.asyncio
async def test_monthly_soft_cap_rejects_over_budget(monkeypatch):
    from app.services.integration import line_bot as lb
    monkeypatch.setenv("LINE_MONTHLY_SOFT_CAP", "185")
    with patch("app.core.redis_client.get_redis",
               new=AsyncMock(return_value=_FakeRedis(185))):
        assert await lb._within_monthly_budget() is False  # 第 186 則 → 拒


@pytest.mark.asyncio
async def test_monthly_soft_cap_allows_within_budget(monkeypatch):
    from app.services.integration import line_bot as lb
    monkeypatch.setenv("LINE_MONTHLY_SOFT_CAP", "185")
    with patch("app.core.redis_client.get_redis",
               new=AsyncMock(return_value=_FakeRedis(10))):
        assert await lb._within_monthly_budget() is True


@pytest.mark.asyncio
async def test_monthly_soft_cap_fail_open_without_redis(monkeypatch):
    from app.services.integration import line_bot as lb
    monkeypatch.setenv("LINE_MONTHLY_SOFT_CAP", "185")
    with patch("app.core.redis_client.get_redis", new=AsyncMock(return_value=None)):
        assert await lb._within_monthly_budget() is True  # 守欄失效不斷通知


@pytest.mark.asyncio
async def test_monthly_soft_cap_disabled_by_zero(monkeypatch):
    from app.services.integration import line_bot as lb
    monkeypatch.setenv("LINE_MONTHLY_SOFT_CAP", "0")
    assert await lb._within_monthly_budget() is True
