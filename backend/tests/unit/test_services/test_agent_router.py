"""
AgentRouter 單元測試

測試路由決策邏輯:
- 閒聊路由
- Pattern 匹配路由
- LLM fallthrough
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.services.ai.agent_router import AgentRouter, RouteDecision


class TestAgentRouter:
    """AgentRouter 路由決策"""

    @pytest.mark.asyncio
    async def test_chitchat_routed(self):
        """閒聊問題被路由至 chitchat"""
        router = AgentRouter()
        with patch("app.services.ai.agent_router.is_chitchat", return_value=True):
            decision = await router.route("你好")
        assert decision.route_type == "chitchat"
        assert decision.confidence == 1.0
        assert decision.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_non_chitchat_falls_through(self):
        """非閒聊、無 pattern 時 fallthrough 至 LLM"""
        router = AgentRouter()
        with patch("app.services.ai.agent_router.is_chitchat", return_value=False):
            decision = await router.route("工務局的函有幾件")
        assert decision.route_type in ("llm", "gemma4")
        assert decision.source in ("fallthrough", "gemma4_intent:document", "gemma4_intent:dispatch", "gemma4_intent:general")

    @pytest.mark.asyncio
    async def test_pattern_match_routed(self):
        """Pattern 匹配成功時路由至 pattern"""
        from app.services.ai.agent_pattern_learner import QueryPattern

        mock_pattern = QueryPattern(
            pattern_key="abc123",
            template="{ORG}的{DOC_TYPE}",
            tool_sequence=["search_documents"],
            params_template={"search_documents": {"query": "test"}},
            hit_count=5,
            success_rate=0.9,
        )

        mock_learner = AsyncMock()
        mock_learner.match = AsyncMock(return_value=[mock_pattern])

        mock_monitor = AsyncMock()
        mock_monitor.get_degraded_tools = AsyncMock(return_value=set())

        router = AgentRouter(pattern_threshold=0.8)
        with patch("app.services.ai.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent_pattern_learner.get_pattern_learner", return_value=mock_learner), \
             patch("app.services.ai.agent_tool_monitor.get_tool_monitor", return_value=mock_monitor):
            decision = await router.route("工務局的函有幾件")

        assert decision.route_type == "pattern"
        assert decision.plan is not None
        assert decision.plan["tool_calls"][0]["name"] == "search_documents"
        assert decision.confidence == 0.9

    @pytest.mark.asyncio
    async def test_pattern_below_threshold_falls_through(self):
        """Pattern 信心度低於門檻時 fallthrough"""
        from app.services.ai.agent_pattern_learner import QueryPattern

        mock_pattern = QueryPattern(
            pattern_key="abc123",
            template="test",
            tool_sequence=["search_documents"],
            params_template={},
            hit_count=5,
            success_rate=0.5,  # Below 0.8 threshold
        )

        mock_learner = AsyncMock()
        mock_learner.match = AsyncMock(return_value=[mock_pattern])

        router = AgentRouter(pattern_threshold=0.8)
        with patch("app.services.ai.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent_pattern_learner.get_pattern_learner", return_value=mock_learner):
            decision = await router.route("query")

        assert decision.route_type == "llm"

    @pytest.mark.asyncio
    async def test_degraded_tool_filtered(self):
        """降級工具被過濾"""
        from app.services.ai.agent_pattern_learner import QueryPattern

        mock_pattern = QueryPattern(
            pattern_key="abc123",
            template="test",
            tool_sequence=["search_documents", "get_entity_detail"],
            params_template={
                "search_documents": {"query": "test"},
                "get_entity_detail": {"entity_id": 1},
            },
            hit_count=5,
            success_rate=0.9,
        )

        mock_learner = AsyncMock()
        mock_learner.match = AsyncMock(return_value=[mock_pattern])

        mock_monitor = AsyncMock()
        mock_monitor.get_degraded_tools = AsyncMock(
            return_value={"get_entity_detail"}
        )

        router = AgentRouter(pattern_threshold=0.8)
        with patch("app.services.ai.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent_pattern_learner.get_pattern_learner", return_value=mock_learner), \
             patch("app.services.ai.agent_tool_monitor.get_tool_monitor", return_value=mock_monitor):
            decision = await router.route("query")

        assert decision.route_type == "pattern"
        assert len(decision.plan["tool_calls"]) == 1
        assert decision.plan["tool_calls"][0]["name"] == "search_documents"

    @pytest.mark.asyncio
    async def test_low_hit_count_falls_through(self):
        """命中次數 < 2 時 fallthrough"""
        from app.services.ai.agent_pattern_learner import QueryPattern

        mock_pattern = QueryPattern(
            pattern_key="abc123",
            template="test",
            tool_sequence=["search_documents"],
            params_template={},
            hit_count=1,  # Only 1 hit, need >= 2
            success_rate=1.0,
        )

        mock_learner = AsyncMock()
        mock_learner.match = AsyncMock(return_value=[mock_pattern])

        router = AgentRouter(pattern_threshold=0.8)
        with patch("app.services.ai.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent_pattern_learner.get_pattern_learner", return_value=mock_learner):
            decision = await router.route("query")

        assert decision.route_type == "llm"

    @pytest.mark.asyncio
    async def test_pattern_learner_error_falls_through(self):
        """PatternLearner 異常時 fallthrough"""
        mock_learner = AsyncMock()
        mock_learner.match = AsyncMock(side_effect=Exception("Redis error"))

        router = AgentRouter()
        with patch("app.services.ai.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent_pattern_learner.get_pattern_learner", return_value=mock_learner):
            decision = await router.route("query")

        assert decision.route_type == "llm"


class TestRouteDecision:
    """RouteDecision 資料結構"""

    def test_default_values(self):
        decision = RouteDecision(route_type="llm")
        assert decision.plan is None
        assert decision.confidence == 0.0
        assert decision.latency_ms == 0.0
        assert decision.source == ""
