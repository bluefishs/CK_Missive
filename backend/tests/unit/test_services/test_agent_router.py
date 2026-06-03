"""
AgentRouter 單元測試

測試路由決策邏輯:
- 閒聊路由
- Pattern 匹配路由
- LLM fallthrough
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.services.ai.agent.agent_router import AgentRouter, RouteDecision


class TestAgentRouter:
    """AgentRouter 路由決策"""

    @pytest.mark.asyncio
    async def test_chitchat_routed(self):
        """閒聊問題被路由至 chitchat"""
        router = AgentRouter()
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=True):
            decision = await router.route("你好")
        assert decision.route_type == "chitchat"
        assert decision.confidence == 1.0
        assert decision.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_non_chitchat_falls_through(self):
        """非閒聊、無快規則、無 pattern、無 gemma4 意圖時 fallthrough 至 LLM

        2026-06-03：原樣本「工務局的函有幾件」含 agency+doc 2 域，被 Layer 1.6
        cross_graph 攔截（2026-05-16 加入）→ 改用單域 document 樣本並 mock 外部依賴
        使測試確定性。
        """
        router = AgentRouter()
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False), \
             patch.object(AgentRouter, "_classify_intent_gemma4",
                          new=AsyncMock(return_value=None)), \
             patch("app.services.ai.agent.agent_pattern_learner.get_pattern_learner",
                   return_value=AsyncMock(match=AsyncMock(return_value=[]))):
            decision = await router.route("這份公文的主旨是什麼")
        assert decision.route_type == "llm"
        assert decision.source == "fallthrough"

    @pytest.mark.asyncio
    async def test_pattern_match_routed(self):
        """Pattern 匹配成功時路由至 pattern"""
        from app.services.ai.agent.agent_pattern_learner import QueryPattern

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
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent.agent_pattern_learner.get_pattern_learner", return_value=mock_learner), \
             patch("app.services.ai.agent.agent_tool_monitor.get_tool_monitor", return_value=mock_monitor):
            # 2026-06-03：改用單域樣本避開 Layer 1.6 cross_graph 攔截，確保進 Layer 2 pattern
            decision = await router.route("這份公文的主旨是什麼")

        assert decision.route_type == "pattern"
        assert decision.plan is not None
        assert decision.plan["tool_calls"][0]["name"] == "search_documents"
        assert decision.confidence == 0.9

    @pytest.mark.asyncio
    async def test_pattern_below_threshold_falls_through(self):
        """Pattern 信心度低於門檻時 fallthrough"""
        from app.services.ai.agent.agent_pattern_learner import QueryPattern

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
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent.agent_pattern_learner.get_pattern_learner", return_value=mock_learner):
            decision = await router.route("query")

        assert decision.route_type == "llm"

    @pytest.mark.asyncio
    async def test_degraded_tool_filtered(self):
        """降級工具被過濾"""
        from app.services.ai.agent.agent_pattern_learner import QueryPattern

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
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent.agent_pattern_learner.get_pattern_learner", return_value=mock_learner), \
             patch("app.services.ai.agent.agent_tool_monitor.get_tool_monitor", return_value=mock_monitor):
            decision = await router.route("query")

        assert decision.route_type == "pattern"
        assert len(decision.plan["tool_calls"]) == 1
        assert decision.plan["tool_calls"][0]["name"] == "search_documents"

    @pytest.mark.asyncio
    async def test_low_hit_count_falls_through(self):
        """命中次數 < 2 時 fallthrough"""
        from app.services.ai.agent.agent_pattern_learner import QueryPattern

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
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent.agent_pattern_learner.get_pattern_learner", return_value=mock_learner):
            decision = await router.route("query")

        assert decision.route_type == "llm"

    @pytest.mark.asyncio
    async def test_pattern_learner_error_falls_through(self):
        """PatternLearner 異常時 fallthrough"""
        mock_learner = AsyncMock()
        mock_learner.match = AsyncMock(side_effect=Exception("Redis error"))

        router = AgentRouter()
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False), \
             patch("app.services.ai.agent.agent_pattern_learner.get_pattern_learner", return_value=mock_learner):
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


class TestFinanceTenderFastPath:
    """Layer 1.7 finance/tender 確定性快路由（LN1, 2026-06-03）+ false-positive 鎖

    缺口修：finance/tender 原無 Layer 1.5 快規則 → 依賴 Layer 2.5 gemma4 intent（不穩）
    →「未付請款」誤落 search_documents（V6_14 議程 #1 真因）。
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("q,tool", [
        ("公司目前未付請款有多少", "get_unpaid_billings"),
        ("有哪些應收帳款還沒收", "get_unpaid_billings"),
        ("費用報銷單還有幾張待審", "get_expense_overview"),
        ("給我財務彙總概況", "get_financial_summary"),
    ])
    async def test_finance_keywords_route_to_finance_tools(self, q, tool):
        """finance 關鍵字 → finance_rule 並映射細分後的真實工具"""
        router = AgentRouter()
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False):
            decision = await router.route(q)
        assert decision.route_type == "pattern"
        assert decision.source == "finance_rule"
        assert decision.plan["tool_calls"][0]["name"] == tool

    @pytest.mark.asyncio
    @pytest.mark.parametrize("q", [
        "最近有哪些決標公告",
        "這個案子底價多少",
        "投標須知在哪裡",
        "招標資訊",
    ])
    async def test_tender_keywords_route_to_search_tender(self, q):
        """tender 關鍵字 → tender_rule 並映射 search_tender"""
        router = AgentRouter()
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False):
            decision = await router.route(q)
        assert decision.route_type == "pattern"
        assert decision.source == "tender_rule"
        assert decision.plan["tool_calls"][0]["name"] == "search_tender"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("q", [
        "環保局公告事項",
        "人事任免通知函",
        "工務局來文辦理會議",
        "請問系統怎麼登入",
    ])
    async def test_non_finance_tender_not_misrouted(self, q):
        """false-positive 鎖：一般公文/行政查詢不得誤命中 finance/tender 快路由"""
        router = AgentRouter()
        with patch("app.services.ai.agent.agent_router.is_chitchat", return_value=False), \
             patch.object(AgentRouter, "_classify_intent_gemma4",
                          new=AsyncMock(return_value=None)), \
             patch("app.services.ai.agent.agent_pattern_learner.get_pattern_learner",
                   return_value=AsyncMock(match=AsyncMock(return_value=[]))):
            decision = await router.route(q)
        assert decision.source not in ("finance_rule", "tender_rule")
