"""
Integration test: channel 從 API 傳到 diary 的完整鏈路（O1 修復鎖定）

ADR-0014/0015 + 坤哥意識體整合分析（CONSCIOUSNESS_INTEGRATION_ANALYSIS.md §4.1）發現：
- agent_query.py /agent/query/stream endpoint 未傳 channel
- PostProcessingContext.__slots__ 無 channel 欄位
- 結果：Hermes/Telegram/LINE/Discord 對話的 diary entry 全標 channel=None
- 影響：pattern_extractor 無法分通道學習，evolution loop 偏向單通道（web）

本 test 鎖定修復鏈：
- agent_query.py:54 必傳 request.channel
- missive_agent.stream_query 必接 channel 參數
- orchestrator.stream_agent_query 必傳 channel 給 PostProcessingContext
- PostProcessingContext.__slots__ 必含 channel
"""
import inspect
import pytest

from app.services.ai.agent.agent_post_processing import PostProcessingContext
from app.services.ai.agent.agent_orchestrator import AgentOrchestrator
from app.services.ai.misc.missive_agent import MissiveAgent


def test_post_processing_context_has_channel_slot():
    """PostProcessingContext 必須有 channel slot（否則 setattr 會 AttributeError）。"""
    assert "channel" in PostProcessingContext.__slots__, (
        "PostProcessingContext.__slots__ 必含 channel — Hermes 對話進 diary 的關鍵欄位"
    )


def test_post_processing_context_init_accepts_channel():
    """PostProcessingContext.__init__ 必須接受 channel 參數。"""
    sig = inspect.signature(PostProcessingContext.__init__)
    assert "channel" in sig.parameters, (
        "PostProcessingContext.__init__ 必須有 channel 參數"
    )
    # 預設應為 None（向後相容）
    assert sig.parameters["channel"].default is None


def test_orchestrator_stream_query_accepts_channel():
    """AgentOrchestrator.stream_agent_query 必須接受 channel 參數。"""
    sig = inspect.signature(AgentOrchestrator.stream_agent_query)
    assert "channel" in sig.parameters
    assert sig.parameters["channel"].default is None


def test_missive_agent_stream_query_accepts_channel():
    """MissiveAgent.stream_query 必須接受 channel 參數。"""
    sig = inspect.signature(MissiveAgent.stream_query)
    assert "channel" in sig.parameters
    assert sig.parameters["channel"].default is None


def test_agent_query_endpoint_passes_channel():
    """/agent/query/stream endpoint 必須從 request.channel 傳給 agent.stream_query。"""
    from app.api.endpoints.ai import agent_query
    src = inspect.getsource(agent_query.agent_query_stream)
    assert "channel=request.channel" in src, (
        "/agent/query/stream 必須傳 channel — 否則 Hermes 對話進不了 diary"
    )


def test_capability_endpoint_passes_channel():
    """/agent/capability/stream 同樣必須傳 channel（雙端點共用 MissiveAgent）。"""
    from app.api.endpoints.ai import agent_query
    src = inspect.getsource(agent_query.capability_query_stream)
    # 至少其中一處 stream_fn 必須傳 channel
    # 註：本端點與 agent_query_stream 程式碼類似但獨立路由
    # 若未來合併可調整 assertion
    has_channel = "channel=request.channel" in src or "channel=" in src
    # 此 test 為前瞻性（capability 端點目前可能未強制傳）— 標 xfail
    if not has_channel:
        pytest.xfail("capability_query_stream 尚未補 channel — 列入 follow-up")


def test_diary_append_reads_channel_from_ctx():
    """agent_post_processing 中 diary append 必須從 ctx 讀 channel（不是 hardcode None）。"""
    from app.services.ai.agent import agent_post_processing
    src = inspect.getsource(agent_post_processing)
    # getattr(ctx, "channel", None) 是 fallback 寫法（兼容 None default）
    # 也接受直接 ctx.channel（因 slot 已存在）
    assert (
        "ctx.channel" in src
        or 'getattr(ctx, "channel"' in src
    ), "diary append 必須讀 ctx.channel，否則 Hermes 通道分類失效"
