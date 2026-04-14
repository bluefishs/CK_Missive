# -*- coding: utf-8 -*-
"""Shadow trace helper TDD — 統一 agent_query_sync 三處 shadow log 呼叫。

職責：
  - 從 Request headers 抽 X-Provider / X-Hermes-Session
  - 用 provider_resolver 推導 provider 標籤
  - fire-and-forget 呼叫 shadow_logger.log_trace
  - 任何錯誤完全吞掉（生產流程不可中斷）
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _FakeRequest:
    def __init__(self, headers: dict):
        self.headers = headers


@pytest.mark.asyncio
async def test_fire_shadow_trace_uses_explicit_header():
    from app.services.ai.agent.shadow_helpers import fire_shadow_trace

    req = _FakeRequest({"X-Provider": "custom-llm"})

    with patch(
        "app.services.ai.agent.shadow_helpers.log_trace",
        new_callable=AsyncMock,
    ) as m, patch(
        "app.services.ai.agent.shadow_helpers.is_enabled", return_value=True
    ):
        await fire_shadow_trace(
            request=req, channel="hermes",
            question="q", answer="a",
            success=True, latency_ms=100,
        )

    assert m.call_args.kwargs["provider"] == "custom-llm"


@pytest.mark.asyncio
async def test_fire_shadow_trace_resolves_from_channel():
    from app.services.ai.agent.shadow_helpers import fire_shadow_trace

    req = _FakeRequest({})
    with patch(
        "app.services.ai.agent.shadow_helpers.log_trace",
        new_callable=AsyncMock,
    ) as m, patch(
        "app.services.ai.agent.shadow_helpers.is_enabled", return_value=True
    ):
        await fire_shadow_trace(
            request=req, channel="hermes",
            question="q", answer="a",
            success=True, latency_ms=100,
        )

    assert m.call_args.kwargs["provider"] == "gemma-hermes"


@pytest.mark.asyncio
async def test_fire_shadow_trace_openclaw_channel():
    from app.services.ai.agent.shadow_helpers import fire_shadow_trace

    req = _FakeRequest({})
    with patch(
        "app.services.ai.agent.shadow_helpers.log_trace",
        new_callable=AsyncMock,
    ) as m, patch(
        "app.services.ai.agent.shadow_helpers.is_enabled", return_value=True
    ):
        await fire_shadow_trace(
            request=req, channel="openclaw",
            question="q", answer="a",
            success=True, latency_ms=100,
        )

    assert m.call_args.kwargs["provider"] == "haiku-openclaw"


@pytest.mark.asyncio
async def test_fire_shadow_trace_noop_when_disabled():
    from app.services.ai.agent.shadow_helpers import fire_shadow_trace

    req = _FakeRequest({})
    with patch(
        "app.services.ai.agent.shadow_helpers.log_trace",
        new_callable=AsyncMock,
    ) as m, patch(
        "app.services.ai.agent.shadow_helpers.is_enabled", return_value=False
    ):
        await fire_shadow_trace(
            request=req, channel="telegram",
            question="q", answer="a",
            success=True, latency_ms=100,
        )
    m.assert_not_called()


@pytest.mark.asyncio
async def test_fire_shadow_trace_swallows_exceptions():
    """log_trace 異常不該向上拋。"""
    from app.services.ai.agent.shadow_helpers import fire_shadow_trace

    req = _FakeRequest({})
    with patch(
        "app.services.ai.agent.shadow_helpers.log_trace",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ), patch(
        "app.services.ai.agent.shadow_helpers.is_enabled", return_value=True
    ):
        # 不該 raise
        await fire_shadow_trace(
            request=req, channel="hermes",
            question="q", answer="a",
            success=True, latency_ms=100,
        )


@pytest.mark.asyncio
async def test_fire_shadow_trace_hermes_session_header():
    """X-Hermes-Session 若存在應寫入 request_id。"""
    from app.services.ai.agent.shadow_helpers import fire_shadow_trace

    req = _FakeRequest({"X-Hermes-Session": "hermes-sid-42"})
    with patch(
        "app.services.ai.agent.shadow_helpers.log_trace",
        new_callable=AsyncMock,
    ) as m, patch(
        "app.services.ai.agent.shadow_helpers.is_enabled", return_value=True
    ):
        await fire_shadow_trace(
            request=req, channel="hermes",
            question="q", answer="a",
            success=True, latency_ms=100,
            session_id="missive-s",
        )

    kw = m.call_args.kwargs
    assert kw["session_id"] == "missive-s"
    assert kw["request_id"] == "hermes-sid-42"
