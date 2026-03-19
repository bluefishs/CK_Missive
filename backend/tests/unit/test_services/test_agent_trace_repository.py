"""
Agent Trace Repository + AgentTrace.to_db_dict 單元測試

測試範圍：
- AgentTrace.to_db_dict() 序列化正確性
- AgentTraceRepository.save_trace() 持久化邏輯
- AgentTraceRepository.link_feedback() 回饋關聯
- AgentTraceRepository.get_recent_traces() 查詢
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.agent_trace import AgentTrace


# ============================================================================
# AgentTrace.to_db_dict 測試
# ============================================================================

class TestToDbDict:
    """to_db_dict() 序列化正確性"""

    def _make_trace(self, **kwargs) -> AgentTrace:
        defaults = {"question": "測試問題", "context": "agent", "query_id": "q-001"}
        defaults.update(kwargs)
        return AgentTrace(**defaults)

    def test_basic_fields(self):
        trace = self._make_trace()
        trace.route_type = "llm"
        trace.iterations = 2
        trace.total_results = 5
        trace.finish()

        d = trace.to_db_dict()
        assert d["query_id"] == "q-001"
        assert d["question"] == "測試問題"
        assert d["context"] == "agent"
        assert d["route_type"] == "llm"
        assert d["iterations"] == 2
        assert d["total_results"] == 5
        assert d["total_ms"] >= 0

    def test_tool_calls_from_spans(self):
        trace = self._make_trace()
        span = trace.start_span("tool:search_documents", query="公文")
        span.finish(status="ok", count=3)

        span2 = trace.start_span("tool:get_statistics")
        span2.finish(status="error", error="timeout")

        trace.finish()
        d = trace.to_db_dict()

        assert len(d["tool_calls"]) == 2
        tc1 = d["tool_calls"][0]
        assert tc1["tool_name"] == "search_documents"
        assert tc1["success"] is True
        assert tc1["result_count"] == 3

        tc2 = d["tool_calls"][1]
        assert tc2["tool_name"] == "get_statistics"
        assert tc2["success"] is False
        assert tc2["error_message"] == "timeout"

    def test_non_tool_spans_excluded(self):
        trace = self._make_trace()
        trace.start_span("planning").finish()
        trace.start_span("synthesis").finish()
        trace.finish()

        d = trace.to_db_dict()
        assert d["tool_calls"] == []

    def test_answer_metadata(self):
        trace = self._make_trace()
        trace._model_used = "ollama"
        trace._answer_length = 150
        trace._answer_preview = "這是答案..."
        trace.finish()

        d = trace.to_db_dict()
        assert d["model_used"] == "ollama"
        assert d["answer_length"] == 150
        assert d["answer_preview"] == "這是答案..."

    def test_tools_used_list(self):
        trace = self._make_trace()
        trace.record_tool_call("search_documents", True, 3)
        trace.record_tool_call("search_entities", True, 1)
        trace.record_tool_call("search_documents", True, 2)
        trace.finish()

        d = trace.to_db_dict()
        tools = d["tools_used"]
        assert set(tools) == {"search_documents", "search_entities"}

    def test_empty_tools_used_is_none(self):
        trace = self._make_trace()
        trace.finish()
        d = trace.to_db_dict()
        assert d["tools_used"] is None

    def test_correction_and_react_flags(self):
        trace = self._make_trace()
        trace.correction_triggered = True
        trace.react_triggered = True
        trace.finish()

        d = trace.to_db_dict()
        assert d["correction_triggered"] is True
        assert d["react_triggered"] is True

    def test_citation_fields(self):
        trace = self._make_trace()
        trace.record_synthesis_validation(5, 3)
        trace.finish()

        d = trace.to_db_dict()
        assert d["citation_count"] == 5
        assert d["citation_verified"] == 3

    def test_default_route_type(self):
        trace = self._make_trace()
        trace.finish()
        d = trace.to_db_dict()
        assert d["route_type"] == "llm"


# ============================================================================
# AgentTrace.flush_to_db 測試
# ============================================================================

class TestFlushToDb:
    """flush_to_db() 持久化邏輯"""

    @pytest.mark.asyncio
    async def test_flush_calls_repository(self):
        trace = AgentTrace(question="test", query_id="q-002")
        trace.finish()

        mock_db = AsyncMock()
        with patch(
            "app.repositories.agent_trace_repository.AgentTraceRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.save_trace = AsyncMock(return_value=42)

            result = await trace.flush_to_db(mock_db)
            assert result == 42
            mock_repo.save_trace.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_handles_error_gracefully(self):
        trace = AgentTrace(question="test", query_id="q-003")
        trace.finish()

        mock_db = AsyncMock()
        with patch(
            "app.repositories.agent_trace_repository.AgentTraceRepository"
        ) as MockRepo:
            MockRepo.return_value.save_trace = AsyncMock(
                side_effect=Exception("DB error")
            )
            result = await trace.flush_to_db(mock_db)
            assert result is None


# ============================================================================
# AgentTraceRepository 單元測試（mock DB）
# ============================================================================

class TestAgentTraceRepository:
    """Repository 基本邏輯測試（不需真實 DB）"""

    def _make_repo(self):
        from app.repositories.agent_trace_repository import AgentTraceRepository
        mock_db = AsyncMock()
        return AgentTraceRepository(mock_db), mock_db

    @pytest.mark.asyncio
    async def test_save_trace_returns_none_on_empty_query_id(self):
        repo, _ = self._make_repo()
        result = await repo.save_trace({"query_id": ""})
        assert result is None

    @pytest.mark.asyncio
    async def test_save_trace_returns_none_on_missing_query_id(self):
        repo, _ = self._make_repo()
        result = await repo.save_trace({})
        assert result is None

    @pytest.mark.asyncio
    async def test_link_feedback_handles_db_error(self):
        repo, mock_db = self._make_repo()
        mock_db.execute = AsyncMock(side_effect=Exception("connection lost"))
        result = await repo.link_feedback("conv-123", 1, "good")
        assert result is False
