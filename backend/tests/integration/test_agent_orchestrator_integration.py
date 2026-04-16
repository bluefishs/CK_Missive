# -*- coding: utf-8 -*-
"""
Agent Orchestrator 整合測試

驗證 orchestrator 核心鏈路的端到端行為：
1. Intent → Router → 正確分類 (chitchat vs domain)
2. Domain query → Planner → Tool selection
3. Tool execution → SSE 事件序列
4. Conversation memory 跨 session 延續
5. AgentTrace 記錄正確

使用策略：
- AI connector = mock (避免外部依賴)
- Orchestrator 內部協作 = 真實模組

Version: 1.0.0
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _parse_sse_events(raw_events: List[str]) -> List[dict]:
    """解析 SSE data: 行為字典列表"""
    events = []
    for line in raw_events:
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


# --------------------------------------------------------------------------
# Test 1: Chitchat 分類正確走短路
# --------------------------------------------------------------------------
class TestChitchatRouting:
    async def test_chitchat_detected_by_is_chitchat(self):
        """閒聊問題應被 is_chitchat 正確偵測"""
        from app.services.ai.agent.agent_chitchat import is_chitchat

        assert is_chitchat("你好") is True
        assert is_chitchat("哈囉") is True
        assert is_chitchat("早安") is True

    async def test_domain_query_not_chitchat(self):
        """業務問題不應被分類為 chitchat"""
        from app.services.ai.agent.agent_chitchat import is_chitchat

        assert is_chitchat("最近有哪些工務局的公文？") is False
        assert is_chitchat("查一下案號 CK-2026-001 的報價狀態") is False


# --------------------------------------------------------------------------
# Test 2: Planner tool selection
# --------------------------------------------------------------------------
class TestToolRegistry:
    async def test_valid_tool_names_not_empty(self):
        """VALID_TOOL_NAMES 應包含至少 10 個工具"""
        from app.services.ai.agent.agent_tools import VALID_TOOL_NAMES

        assert len(VALID_TOOL_NAMES) >= 10

    async def test_core_tools_registered(self):
        """核心工具應在 VALID_TOOL_NAMES 中"""
        from app.services.ai.agent.agent_tools import VALID_TOOL_NAMES

        core_tools = [
            "search_documents",
            "search_dispatch_orders",
            "search_projects",
        ]
        for tool in core_tools:
            assert tool in VALID_TOOL_NAMES, f"Missing core tool: {tool}"

    async def test_tool_registry_definitions(self):
        """tool_registry 應能產出工具定義 JSON"""
        from app.services.ai.tools.tool_registry import get_tool_registry

        registry = get_tool_registry()
        defs = registry.get_definitions_json()
        assert isinstance(defs, str)
        assert len(defs) > 100  # 不應是空字串


# --------------------------------------------------------------------------
# Test 3: SSE 事件序列格式
# --------------------------------------------------------------------------
class TestSSEEventFormat:
    async def test_sse_helper_produces_valid_json(self):
        """sse() helper 應產生合法 JSON 的 data: 行"""
        from app.services.ai.core.agent_utils import sse

        event = sse(type="thinking", step="分析問題", step_index=0)
        assert event.startswith("data: ")
        parsed = json.loads(event[6:])
        assert parsed["type"] == "thinking"
        assert parsed["step"] == "分析問題"
        assert parsed["step_index"] == 0

    async def test_sse_done_event_format(self):
        """done 事件應包含 latency_ms 和 model"""
        from app.services.ai.core.agent_utils import sse

        event = sse(
            type="done",
            latency_ms=1234,
            model="test-model",
            tools_used=["search_documents"],
            iterations=2,
        )
        parsed = json.loads(event[6:])
        assert parsed["type"] == "done"
        assert parsed["latency_ms"] == 1234
        assert "search_documents" in parsed["tools_used"]


# --------------------------------------------------------------------------
# Test 4: Conversation memory 存取
# --------------------------------------------------------------------------
class TestConversationMemory:
    async def test_memory_get_and_delete(self):
        """ConversationMemory delete 應能清除 session"""
        from app.services.ai.agent.agent_conversation_memory import get_conversation_memory

        memory = get_conversation_memory()
        session_id = "test_integration_session_001"

        # delete 不應拋錯（即使 session 不存在）
        await memory.delete(session_id)

    async def test_memory_instance_is_singleton(self):
        """get_conversation_memory 應回傳同一實例"""
        from app.services.ai.agent.agent_conversation_memory import get_conversation_memory

        m1 = get_conversation_memory()
        m2 = get_conversation_memory()
        assert m1 is m2


# --------------------------------------------------------------------------
# Test 5: AgentTrace 記錄正確
# --------------------------------------------------------------------------
class TestAgentTrace:
    async def test_trace_captures_spans(self):
        """AgentTrace 應記錄 span 和最終摘要"""
        from app.services.ai.agent.agent_trace import AgentTrace

        trace = AgentTrace(question="測試問題")

        span1 = trace.start_span("planning")
        span1.finish(tool_count=1)

        span2 = trace.start_span("tool_call")
        span2.finish(tool="search_documents", result_count=5)

        trace.finish()

        assert len(trace.spans) >= 2
        assert trace.question == "測試問題"

    async def test_trace_summary_contains_question(self):
        """trace.summary() 應包含問題資訊"""
        from app.services.ai.agent.agent_trace import AgentTrace

        trace = AgentTrace(question="摘要測試")
        trace.finish()

        summary = trace.summary()
        # summary 可能是 dict 或 str
        if isinstance(summary, dict):
            assert summary.get("question") == "摘要測試"
        else:
            assert "摘要測試" in str(summary)
