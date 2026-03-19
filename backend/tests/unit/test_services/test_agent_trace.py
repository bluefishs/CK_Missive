"""
AgentTrace 單元測試

測試結構化追蹤記錄的所有功能：
- TraceSpan 計時與狀態
- AgentTrace 記錄方法
- 指標計算（成功率、引用準確率）
- summary 輸出格式
"""

import time
from unittest.mock import patch

import pytest

from app.services.ai.agent_trace import AgentTrace, TraceSpan


class TestTraceSpan:
    """TraceSpan 基礎功能"""

    def test_finish_sets_duration_and_status(self):
        span = TraceSpan(name="test", start_ms=1000.0)
        with patch("time.time", return_value=1.5):
            span.finish()
        assert span.end_ms == 1500.0
        assert span.duration_ms == 500.0
        assert span.status == "ok"

    def test_finish_with_error_status(self):
        span = TraceSpan(name="test", start_ms=1000.0)
        with patch("time.time", return_value=2.0):
            span.finish(status="error", reason="timeout")
        assert span.status == "error"
        assert span.metadata["reason"] == "timeout"

    def test_finish_merges_metadata(self):
        span = TraceSpan(name="test", start_ms=0, metadata={"existing": True})
        with patch("time.time", return_value=0.001):
            span.finish(count=5)
        assert span.metadata["existing"] is True
        assert span.metadata["count"] == 5


class TestAgentTrace:
    """AgentTrace 完整追蹤"""

    def test_start_span_appends(self):
        trace = AgentTrace(question="test")
        span = trace.start_span("planning")
        assert len(trace.spans) == 1
        assert span.name == "planning"

    def test_record_tool_call_success(self):
        trace = AgentTrace(question="test")
        trace.record_tool_call("search_documents", True, 5)
        assert trace.tools_called == ["search_documents"]
        assert trace.tools_succeeded == ["search_documents"]
        assert trace.tools_failed == []
        assert trace.total_results == 5

    def test_record_tool_call_failure(self):
        trace = AgentTrace(question="test")
        trace.record_tool_call("search_documents", False)
        assert trace.tools_called == ["search_documents"]
        assert trace.tools_succeeded == []
        assert trace.tools_failed == ["search_documents"]
        assert trace.total_results == 0

    def test_record_correction(self):
        trace = AgentTrace(question="test")
        trace.record_correction("broaden_query")
        assert trace.correction_triggered is True
        assert any(s.name == "correction" for s in trace.spans)

    def test_record_react(self):
        trace = AgentTrace(question="test")
        trace.record_react("continue", 0.8)
        assert trace.react_triggered is True
        assert any(s.name == "react" for s in trace.spans)

    def test_record_synthesis_validation(self):
        trace = AgentTrace(question="test")
        trace.record_synthesis_validation(3, 2)
        assert trace.synthesis_validated is True
        assert trace.citation_count == 3
        assert trace.citation_verified == 2

    def test_finish_sets_total_ms(self):
        trace = AgentTrace(question="test")
        trace._start_time = 100.0
        with patch("time.time", return_value=100.5):
            trace.finish()
        assert trace.total_ms == 500

    def test_tool_success_rate_all_success(self):
        trace = AgentTrace(question="test")
        trace.record_tool_call("a", True, 1)
        trace.record_tool_call("b", True, 2)
        assert trace.tool_success_rate == 1.0

    def test_tool_success_rate_mixed(self):
        trace = AgentTrace(question="test")
        trace.record_tool_call("a", True, 1)
        trace.record_tool_call("b", False)
        assert trace.tool_success_rate == 0.5

    def test_tool_success_rate_no_calls(self):
        trace = AgentTrace(question="test")
        assert trace.tool_success_rate == 1.0

    def test_citation_accuracy_no_citations(self):
        trace = AgentTrace(question="test")
        assert trace.citation_accuracy == 1.0

    def test_citation_accuracy_partial(self):
        trace = AgentTrace(question="test")
        trace.record_synthesis_validation(4, 3)
        assert trace.citation_accuracy == 0.75

    def test_summary_format(self):
        trace = AgentTrace(
            question="工務局的函",
            context="doc",
            query_id="q123",
            role_identity="乾坤公文秘書",
        )
        trace.record_tool_call("search_documents", True, 3)
        trace.iterations = 1
        trace._start_time = 100.0
        with patch("time.time", return_value=101.0):
            trace.finish()

        s = trace.summary()
        assert s["query_id"] == "q123"
        assert s["question"] == "工務局的函"
        assert s["context"] == "doc"
        assert s["role"] == "乾坤公文秘書"
        assert s["total_ms"] == 1000
        assert s["iterations"] == 1
        assert s["tool_count"] == 1
        assert s["tool_success_rate"] == 1.0
        assert s["total_results"] == 3
        assert isinstance(s["spans"], list)

    def test_log_summary_does_not_raise(self):
        trace = AgentTrace(question="test")
        trace.finish()
        # Should not raise
        trace.log_summary()

    def test_summary_truncates_long_question(self):
        long_q = "x" * 200
        trace = AgentTrace(question=long_q)
        trace.finish()
        s = trace.summary()
        assert len(s["question"]) == 100
