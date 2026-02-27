"""
Agent Orchestrator 主編排模組單元測試

測試範圍：
- AgentOrchestrator._collect_sources: 來源收集（去重）
- AgentOrchestrator._execute_tool: 超時與異常處理
- stream_agent_query: 閒聊短路、速率限制、完整工具流程

共 20+ test cases
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.agent_orchestrator import AgentOrchestrator


# ── Fixtures ──

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


def make_orchestrator(mock_db):
    """建立帶 mock 依賴的 orchestrator"""
    with patch("app.services.ai.agent_orchestrator.get_ai_connector") as mock_ai_fn, \
         patch("app.services.ai.agent_orchestrator.get_ai_config") as mock_config_fn, \
         patch("app.services.ai.agent_orchestrator.EmbeddingManager") as mock_emb_cls, \
         patch("app.services.ai.base_ai_service.get_rate_limiter") as mock_rl_fn:

        mock_ai = AsyncMock()
        mock_ai_fn.return_value = mock_ai

        mock_config = MagicMock()
        mock_config.rag_max_history_turns = 4
        mock_config.rag_temperature = 0.3
        mock_config.rag_max_tokens = 512
        mock_config.rag_max_context_chars = 5000
        mock_config.hybrid_semantic_weight = 0.3
        mock_config_fn.return_value = mock_config

        mock_rl = AsyncMock()
        mock_rl.acquire = AsyncMock(return_value=(True, 0))
        mock_rl_fn.return_value = mock_rl

        orchestrator = AgentOrchestrator(mock_db)
        orchestrator.ai = mock_ai
        orchestrator._rate_limiter = mock_rl

        return orchestrator


# ============================================================================
# _collect_sources
# ============================================================================

class TestCollectSources:
    """來源收集測試"""

    def test_collect_from_search_documents(self):
        sources = []
        result = {
            "documents": [
                {"id": 1, "doc_number": "DOC1", "subject": "S1", "doc_type": "函",
                 "category": "A", "sender": "X", "receiver": "Y", "doc_date": "2026-01-01",
                 "similarity": 0.9},
            ],
        }
        AgentOrchestrator._collect_sources("search_documents", result, sources)
        assert len(sources) == 1
        assert sources[0]["document_id"] == 1

    def test_collect_from_find_similar(self):
        sources = []
        result = {
            "documents": [
                {"id": 2, "doc_number": "DOC2", "subject": "S2", "doc_type": "令",
                 "category": "B", "sender": "A", "receiver": "B", "doc_date": "2026-02-01",
                 "similarity": 0.8},
            ],
        }
        AgentOrchestrator._collect_sources("find_similar", result, sources)
        assert len(sources) == 1

    def test_no_duplicate_sources(self):
        sources = [{"document_id": 1, "doc_number": "DOC1", "subject": "S1"}]
        result = {
            "documents": [
                {"id": 1, "doc_number": "DOC1", "subject": "S1",
                 "doc_type": "", "category": "", "sender": "", "receiver": "",
                 "doc_date": "", "similarity": 0},
            ],
        }
        AgentOrchestrator._collect_sources("search_documents", result, sources)
        assert len(sources) == 1  # 不重複

    def test_non_document_tools_ignored(self):
        sources = []
        result = {"entities": [{"id": 1}], "count": 1}
        AgentOrchestrator._collect_sources("search_entities", result, sources)
        assert len(sources) == 0

    def test_empty_documents(self):
        sources = []
        AgentOrchestrator._collect_sources("search_documents", {"documents": []}, sources)
        assert len(sources) == 0

    def test_no_documents_key(self):
        sources = []
        AgentOrchestrator._collect_sources("search_documents", {"count": 0}, sources)
        assert len(sources) == 0


# ============================================================================
# _execute_tool
# ============================================================================

class TestExecuteTool:
    """工具執行包裝測試"""

    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_db):
        orchestrator = make_orchestrator(mock_db)
        orchestrator._tools = MagicMock()
        orchestrator._tools.execute = AsyncMock(
            return_value={"count": 5, "documents": []}
        )
        result = await orchestrator._execute_tool("search_documents", {"keywords": ["test"]})
        assert result["count"] == 5

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_db):
        import asyncio
        orchestrator = make_orchestrator(mock_db)

        async def slow_tool(*args, **kwargs):
            await asyncio.sleep(100)

        orchestrator._tools = MagicMock()
        orchestrator._tools.execute = slow_tool

        # Patch TOOL_TIMEOUT to a very short value
        with patch("app.services.ai.agent_orchestrator.TOOL_TIMEOUT", 0.01):
            result = await orchestrator._execute_tool("search_documents", {})
            assert "error" in result
            assert "超時" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_handling(self, mock_db):
        orchestrator = make_orchestrator(mock_db)
        orchestrator._tools = MagicMock()
        orchestrator._tools.execute = AsyncMock(side_effect=ValueError("test error"))

        result = await orchestrator._execute_tool("search_documents", {})
        assert "error" in result
        assert "test error" in result["error"]


# ============================================================================
# stream_agent_query (整合流程)
# ============================================================================

class TestStreamAgentQuery:
    """主編排流程測試"""

    @pytest.mark.asyncio
    async def test_chitchat_shortcut(self, mock_db):
        """閒聊走快速路徑"""
        orchestrator = make_orchestrator(mock_db)
        orchestrator.ai.chat_completion = AsyncMock(return_value="你好！有什麼公文需要幫忙嗎？")

        events = []
        async for event in orchestrator.stream_agent_query("你好"):
            events.append(event)

        # 解析 SSE events
        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events if e.strip()]
        types = [p["type"] for p in parsed]

        assert "thinking" in types
        assert "token" in types
        assert "done" in types
        # 不應有 tool_call（閒聊不走工具）
        assert "tool_call" not in types

    @pytest.mark.asyncio
    async def test_rate_limited(self, mock_db):
        """速率限制回應"""
        orchestrator = make_orchestrator(mock_db)
        orchestrator._rate_limiter.acquire = AsyncMock(return_value=(False, 30))

        events = []
        async for event in orchestrator.stream_agent_query("查詢公文"):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events if e.strip()]
        error_events = [p for p in parsed if p["type"] == "error"]
        assert len(error_events) == 1
        assert error_events[0]["code"] == "RATE_LIMITED"

    @pytest.mark.asyncio
    async def test_no_tools_planned_fallback_rag(self, mock_db):
        """LLM 判定無需工具 → 回退 RAG"""
        orchestrator = make_orchestrator(mock_db)
        orchestrator._planner = MagicMock()
        orchestrator._planner.preprocess_question = AsyncMock(return_value={})
        orchestrator._planner.plan_tools = AsyncMock(return_value={"tool_calls": []})

        # Mock fallback RAG
        async def mock_rag(q, h, t):
            yield 'data: {"type": "token", "token": "RAG回答"}\n\n'
            yield 'data: {"type": "done", "latency_ms": 100}\n\n'

        orchestrator._fallback_rag = mock_rag

        events = []
        # 使用含業務關鍵字的問題，避免被閒聊偵測攔截
        async for event in orchestrator.stream_agent_query("公文管理系統的一般問題"):
            events.append(event)

        all_text = "".join(events)
        assert "RAG回答" in all_text

    @pytest.mark.asyncio
    async def test_full_tool_flow(self, mock_db):
        """完整工具流程：規劃 → 執行 → 合成"""
        orchestrator = make_orchestrator(mock_db)

        # Mock planner
        orchestrator._planner = MagicMock()
        orchestrator._planner.preprocess_question = AsyncMock(return_value={})
        orchestrator._planner.plan_tools = AsyncMock(return_value={
            "reasoning": "搜尋公文",
            "tool_calls": [{"name": "search_documents", "params": {"keywords": ["工務局"]}}],
        })
        orchestrator._planner.evaluate_and_replan = MagicMock(return_value=None)

        # Mock tool executor
        orchestrator._tools = MagicMock()
        orchestrator._tools.execute = AsyncMock(return_value={
            "count": 2,
            "documents": [
                {"id": 1, "doc_number": "DOC1", "subject": "文件1",
                 "doc_type": "函", "category": "", "sender": "A",
                 "receiver": "B", "doc_date": "2026-01-01", "similarity": 0},
            ],
        })

        # Mock synthesizer
        async def mock_synth(*args, **kwargs):
            yield "工務局相關公文如下：\n- [公文1] DOC1"

        orchestrator._synthesizer = MagicMock()
        orchestrator._synthesizer.synthesize_answer = mock_synth

        events = []
        async for event in orchestrator.stream_agent_query("工務局的函"):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events if e.strip()]
        types = [p["type"] for p in parsed]

        assert "thinking" in types
        assert "tool_call" in types
        assert "tool_result" in types
        assert "sources" in types
        assert "token" in types
        assert "done" in types

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_db):
        """全域錯誤處理"""
        orchestrator = make_orchestrator(mock_db)
        # 使 rate_limiter.acquire 拋出異常
        orchestrator._rate_limiter.acquire = AsyncMock(side_effect=RuntimeError("boom"))

        events = []
        async for event in orchestrator.stream_agent_query("查詢公文"):
            events.append(event)

        parsed = [json.loads(e.replace("data: ", "").strip()) for e in events if e.strip()]
        error_events = [p for p in parsed if p["type"] == "error"]
        assert len(error_events) == 1
        assert error_events[0]["code"] == "SERVICE_ERROR"
