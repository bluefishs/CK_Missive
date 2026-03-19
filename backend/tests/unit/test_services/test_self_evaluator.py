"""
AgentSelfEvaluator 單元測試
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.ai.agent_self_evaluator import (
    AgentSelfEvaluator,
    EvalScore,
    get_self_evaluator,
)


class TestEvalScore:
    def test_needs_improvement_low_score(self):
        score = EvalScore(overall=0.5)
        assert score.needs_improvement is True

    def test_needs_improvement_high_score(self):
        score = EvalScore(overall=0.85)
        assert score.needs_improvement is False

    def test_needs_improvement_boundary(self):
        score = EvalScore(overall=0.7)
        assert score.needs_improvement is False


class TestAgentSelfEvaluator:
    def setup_method(self):
        self.evaluator = AgentSelfEvaluator()

    def _make_trace(self, total_ms=1000, tools_failed=None):
        trace = MagicMock()
        trace.total_ms = total_ms
        trace.tools_failed = tools_failed or []
        return trace

    # ── Relevance ──

    def test_relevance_empty_answer(self):
        score = self.evaluator._eval_relevance("工務局公文", "")
        assert score < 0.5

    def test_relevance_matching_keywords(self):
        score = self.evaluator._eval_relevance(
            "工務局公文",
            "工務局在本月發出了三份公文，包含用地計畫和工程施工等類別的文件。"
        )
        assert score > 0.4  # 部分關鍵詞匹配，分數應高於基線

    def test_relevance_no_chinese(self):
        score = self.evaluator._eval_relevance(
            "hello world test",
            "This is a test response with enough length to pass the minimum threshold."
        )
        assert score == 0.8  # 非中文給予中性分數

    # ── Completeness ──

    def test_completeness_no_answer(self):
        score = self.evaluator._eval_completeness("", [])
        assert score == 0.0

    def test_completeness_with_tools(self):
        results = [
            {"tool": "search_documents", "result": [{"id": 1}]},
            {"tool": "get_statistics", "result": {"total": 5}},
        ]
        score = self.evaluator._eval_completeness(
            "工務局有很多公文" * 10, results
        )
        assert score > 0.5

    def test_completeness_all_empty_tools(self):
        results = [
            {"tool": "search_documents", "result": []},
        ]
        score = self.evaluator._eval_completeness("短回答", results)
        assert score < 0.5

    # ── Citation ──

    def test_citation_valid(self):
        score = self.evaluator._eval_citation({"valid": True})
        assert score == 1.0

    def test_citation_none(self):
        score = self.evaluator._eval_citation(None)
        assert score == 0.7

    def test_citation_partial(self):
        score = self.evaluator._eval_citation(
            {"valid": False, "total": 4, "verified": 2}
        )
        assert score == 0.5

    # ── Latency ──

    def test_latency_ok(self):
        trace = self._make_trace(total_ms=2000)
        assert self.evaluator._eval_latency(trace) is True

    def test_latency_exceeded(self):
        trace = self._make_trace(total_ms=6000)
        assert self.evaluator._eval_latency(trace) is False

    # ── Tool Efficiency ──

    def test_tool_efficiency_no_tools(self):
        trace = self._make_trace()
        score = self.evaluator._eval_tool_efficiency([], trace)
        assert score == 0.8

    def test_tool_efficiency_all_success(self):
        results = [{"tool": "a"}, {"tool": "b"}]
        trace = self._make_trace(tools_failed=[])
        score = self.evaluator._eval_tool_efficiency(results, trace)
        assert score == 1.0

    def test_tool_efficiency_some_failed(self):
        results = [{"tool": "a"}, {"tool": "b"}, {"tool": "c"}]
        trace = self._make_trace(tools_failed=["b"])
        score = self.evaluator._eval_tool_efficiency(results, trace)
        assert score < 1.0

    def test_tool_efficiency_too_many_tools(self):
        results = [{"tool": f"t{i}"} for i in range(6)]
        trace = self._make_trace(tools_failed=[])
        score = self.evaluator._eval_tool_efficiency(results, trace)
        assert score < 1.0  # 超過 MAX_REASONABLE_TOOLS 扣分

    # ── Full Evaluate ──

    def test_evaluate_good_answer(self):
        trace = self._make_trace(total_ms=1500)
        score = self.evaluator.evaluate(
            question="工務局最近的公文有哪些",
            answer="工務局本月發出了5份公文，包含用地、工程等類別。" * 5,
            tool_results=[
                {"tool": "search_documents", "result": [{"id": 1}]},
            ],
            trace=trace,
            citation_result={"valid": True},
        )
        assert score.overall > 0.7
        assert not score.needs_improvement

    def test_evaluate_bad_answer(self):
        trace = self._make_trace(total_ms=8000, tools_failed=["search_documents"])
        score = self.evaluator.evaluate(
            question="工務局最近的公文有哪些",
            answer="不好意思",
            tool_results=[
                {"tool": "search_documents", "result": []},
            ],
            trace=trace,
            citation_result={"valid": False, "total": 3, "verified": 0},
        )
        assert score.overall < 0.5
        assert score.needs_improvement
        assert len(score.signals) > 0

    def test_evaluate_generates_signals(self):
        trace = self._make_trace(total_ms=6000)
        score = self.evaluator.evaluate(
            question="測試",
            answer="短",
            tool_results=[],
            trace=trace,
        )
        signal_types = [s["type"] for s in score.signals]
        assert "high_latency" in signal_types

    # ── Singleton ──

    def test_get_self_evaluator_singleton(self):
        e1 = get_self_evaluator()
        e2 = get_self_evaluator()
        assert e1 is e2


class TestEvaluateAndStore:
    @pytest.mark.asyncio
    async def test_evaluate_and_store_with_redis(self):
        evaluator = AgentSelfEvaluator()
        redis = AsyncMock()
        trace = MagicMock()
        trace.total_ms = 1000
        trace.tools_failed = []

        score = await evaluator.evaluate_and_store(
            question="測試查詢",
            answer="測試回答" * 20,
            tool_results=[{"tool": "search_documents", "result": [{"id": 1}]}],
            trace=trace,
            citation_result={"valid": True},
            redis=redis,
        )

        assert score.overall > 0
        # 應該有呼叫 redis
        assert redis.lpush.called or redis.ltrim.called

    @pytest.mark.asyncio
    async def test_evaluate_and_store_no_redis(self):
        evaluator = AgentSelfEvaluator()
        trace = MagicMock()
        trace.total_ms = 1000
        trace.tools_failed = []

        score = await evaluator.evaluate_and_store(
            question="測試", answer="回答", tool_results=[],
            trace=trace, redis=None,
        )
        assert score.overall > 0  # 仍然能評估，只是不儲存
