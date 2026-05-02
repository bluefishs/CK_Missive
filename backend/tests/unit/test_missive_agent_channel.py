# -*- coding: utf-8 -*-
"""MissiveAgent channel propagation tests (v6.4 A1)

驗證跨通道對話 channel 標籤從 sync endpoint → MissiveAgent → orchestrator
完整鏈路傳遞，避免 LINE/Hermes/Telegram 通道對話 diary 全標 channel=None。
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_missive_agent_passes_channel_to_orchestrator(monkeypatch):
    """MissiveAgent.stream_query 接收 channel kwarg 並傳給 orchestrator.stream_agent_query。"""
    from app.services.ai.misc.missive_agent import MissiveAgent

    captured = {}

    async def fake_stream_agent_query(
        question, history=None, session_id=None, context=None, channel=None,
    ):
        captured["channel"] = channel
        captured["session_id"] = session_id
        captured["context"] = context
        # 串流 0 events 即可（agent 內外殼層另外 yield self_awareness 等）
        if False:
            yield ""

    # 直接造 MissiveAgent 並換掉內部 orchestrator
    db = MagicMock()
    agent = MissiveAgent(db)
    agent.orchestrator = MagicMock()
    agent.orchestrator.stream_agent_query = fake_stream_agent_query

    # 跳過 self_profile / proactive scan（避免 DB 連線）
    async def fake_profile(*a, **kw):
        return {"identity": "乾坤", "total_queries": 0, "personality_hint": "", "top_domains": []}
    async def fake_alerts(*a, **kw):
        return {"alerts": []}

    import app.services.ai.agent.agent_self_profile as p_mod
    import app.services.ai.agent.agent_proactive_scanner as a_mod
    monkeypatch.setattr(p_mod, "get_self_profile", fake_profile)
    monkeypatch.setattr(a_mod, "scan_agent_alerts", fake_alerts)

    # 收 events
    events = []
    async for ev in agent.stream_query(
        question="測試 channel 傳遞",
        session_id="line-Uabc-conv",
        channel="line",
    ):
        events.append(ev)

    assert captured.get("channel") == "line"
    assert captured.get("session_id") == "line-Uabc-conv"


@pytest.mark.asyncio
async def test_missive_agent_channel_defaults_none(monkeypatch):
    """未傳 channel → orchestrator 收到 None（不該偽造 channel）。"""
    from app.services.ai.misc.missive_agent import MissiveAgent

    captured = {}

    async def fake_stream_agent_query(
        question, history=None, session_id=None, context=None, channel=None,
    ):
        captured["channel"] = channel
        if False:
            yield ""

    db = MagicMock()
    agent = MissiveAgent(db)
    agent.orchestrator = MagicMock()
    agent.orchestrator.stream_agent_query = fake_stream_agent_query

    async def fake_profile(*a, **kw):
        return {"identity": "乾坤", "total_queries": 0, "personality_hint": "", "top_domains": []}
    async def fake_alerts(*a, **kw):
        return {"alerts": []}

    import app.services.ai.agent.agent_self_profile as p_mod
    import app.services.ai.agent.agent_proactive_scanner as a_mod
    monkeypatch.setattr(p_mod, "get_self_profile", fake_profile)
    monkeypatch.setattr(a_mod, "scan_agent_alerts", fake_alerts)

    async for _ in agent.stream_query(question="無 channel 測試"):
        pass

    assert captured.get("channel") is None


@pytest.mark.asyncio
async def test_missive_agent_passes_channel_hermes(monkeypatch):
    """channel=hermes（跨 repo gateway）傳遞正確。"""
    from app.services.ai.misc.missive_agent import MissiveAgent

    captured = {}

    async def fake_stream_agent_query(
        question, history=None, session_id=None, context=None, channel=None,
    ):
        captured["channel"] = channel
        if False:
            yield ""

    db = MagicMock()
    agent = MissiveAgent(db)
    agent.orchestrator = MagicMock()
    agent.orchestrator.stream_agent_query = fake_stream_agent_query

    async def fake_profile(*a, **kw):
        return {"identity": "乾坤", "total_queries": 0, "personality_hint": "", "top_domains": []}
    async def fake_alerts(*a, **kw):
        return {"alerts": []}
    import app.services.ai.agent.agent_self_profile as p_mod
    import app.services.ai.agent.agent_proactive_scanner as a_mod
    monkeypatch.setattr(p_mod, "get_self_profile", fake_profile)
    monkeypatch.setattr(a_mod, "scan_agent_alerts", fake_alerts)

    async for _ in agent.stream_query(
        question="hermes gateway 來的查詢", channel="hermes",
    ):
        pass

    assert captured.get("channel") == "hermes"
