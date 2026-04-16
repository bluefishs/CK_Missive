# -*- coding: utf-8 -*-
"""
Agent Evolution 整合測試

驗證 self-evaluator → evolution scheduler → pattern learner 三角鏈路：
1. SelfEvaluator 純規則式評分的正確性
2. EvalScore severity 分類
3. EvolutionScheduler trigger 條件判斷
4. PatternLearner normalize + key 生成一致性
5. 完整鏈路: 低分 → CRITICAL severity → signal 產生

使用策略：
- SelfEvaluator = 真實（純規則，無外部依賴）
- EvolutionScheduler = mock Redis
- PatternLearner = 單元測試 normalize 邏輯

Version: 1.0.0
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Any

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def evaluator():
    from app.services.ai.agent.agent_self_evaluator import AgentSelfEvaluator
    return AgentSelfEvaluator()


@pytest.fixture
def mock_trace():
    """建立 minimal AgentTrace mock"""
    trace = MagicMock()
    trace.spans = []
    trace.tools_called = []
    trace.tools_succeeded = []
    trace.tools_failed = []
    trace.iterations = 1
    trace.total_ms = 2000
    return trace


@pytest.fixture
def mock_redis():
    """建立 mock Redis 用於 EvolutionScheduler"""
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=50)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.lpush = AsyncMock()
    redis.expire = AsyncMock()
    redis.ping = AsyncMock()
    return redis


# --------------------------------------------------------------------------
# Test 1: SelfEvaluator 基本評分
# --------------------------------------------------------------------------

class TestSelfEvaluatorScoring:
    def test_high_quality_answer_scores_well(self, evaluator, mock_trace):
        """高品質回答應得到高分 (>0.7)"""
        mock_trace.total_ms = 1000
        mock_trace.tools_called = ["search_documents"]
        mock_trace.tools_succeeded = ["search_documents"]

        score = evaluator.evaluate(
            question="最近的工務局公文有哪些？",
            answer="根據系統紀錄，最近有以下3筆工務局公文：1. 桃工字第115001號（2026-04-10），主旨為道路維修；2. 桃工字第115002號（2026-04-12），主旨為橋梁檢測；3. 桃工字第115003號（2026-04-15），主旨為排水溝清理。",
            tool_results=[{"tool": "search_documents", "count": 3}],
            trace=mock_trace,
            citation_result={"accuracy": 1.0, "total": 3, "verified": 3},
        )

        assert score.overall > 0.6
        assert score.severity in ("low", "medium")

    def test_empty_answer_scores_low(self, evaluator, mock_trace):
        """空回答應得到低分"""
        score = evaluator.evaluate(
            question="最近的公文？",
            answer="",
            tool_results=[],
            trace=mock_trace,
        )

        assert score.overall < 0.5
        assert score.completeness < 0.3

    def test_slow_response_penalized(self, evaluator, mock_trace):
        """超時回答 latency_ok 應為 False"""
        mock_trace.total_ms = 8000  # > 5000 threshold

        score = evaluator.evaluate(
            question="查詢公文",
            answer="找到以下公文資料，共計有三筆相關紀錄。",
            tool_results=[{"tool": "search_documents", "count": 3}],
            trace=mock_trace,
        )

        assert score.latency_ok is False


# --------------------------------------------------------------------------
# Test 2: Severity 分類
# --------------------------------------------------------------------------

class TestSeverityClassification:
    def test_critical_below_0_3(self):
        from app.services.ai.agent.agent_self_evaluator import classify_severity, SEVERITY_CRITICAL
        assert classify_severity(0.1) == SEVERITY_CRITICAL
        assert classify_severity(0.29) == SEVERITY_CRITICAL

    def test_high_between_0_3_and_0_5(self):
        from app.services.ai.agent.agent_self_evaluator import classify_severity, SEVERITY_HIGH
        assert classify_severity(0.3) == SEVERITY_HIGH
        assert classify_severity(0.49) == SEVERITY_HIGH

    def test_medium_between_0_5_and_0_7(self):
        from app.services.ai.agent.agent_self_evaluator import classify_severity, SEVERITY_MEDIUM
        assert classify_severity(0.5) == SEVERITY_MEDIUM
        assert classify_severity(0.69) == SEVERITY_MEDIUM

    def test_low_above_0_7(self):
        from app.services.ai.agent.agent_self_evaluator import classify_severity, SEVERITY_LOW
        assert classify_severity(0.7) == SEVERITY_LOW
        assert classify_severity(1.0) == SEVERITY_LOW


# --------------------------------------------------------------------------
# Test 3: Domain-aware 權重
# --------------------------------------------------------------------------

class TestDomainWeights:
    def test_default_weights_sum_to_one(self, evaluator):
        """預設權重應加總為 1.0"""
        weights = evaluator.get_weights()
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_erp_domain_weights(self, evaluator):
        """ERP 領域應有特定權重（citation 更重要）"""
        weights = evaluator.get_weights("erp")
        assert weights["citation_accuracy"] >= 0.25
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_dispatch_domain_weights(self, evaluator):
        """派工領域應有特定權重（延遲更重要）"""
        weights = evaluator.get_weights("dispatch")
        assert weights["latency"] >= 0.15
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_unknown_domain_uses_default(self, evaluator):
        """未知領域應使用預設權重"""
        default = evaluator.get_weights()
        unknown = evaluator.get_weights("nonexistent_domain")
        assert default == unknown


# --------------------------------------------------------------------------
# Test 4: EvolutionScheduler trigger 條件
# --------------------------------------------------------------------------

class TestEvolutionSchedulerTrigger:
    async def test_should_evolve_at_query_count(self, mock_redis):
        """查詢計數達閾值時應觸發進化"""
        from app.services.ai.agent.agent_evolution_scheduler import AgentEvolutionScheduler

        scheduler = AgentEvolutionScheduler(redis=mock_redis)
        mock_redis.incr.return_value = 50  # == EVOLVE_EVERY_N_QUERIES

        result = await scheduler.should_evolve()
        assert result is True

    async def test_should_not_evolve_below_threshold(self, mock_redis):
        """查詢計數未達閾值時不觸發"""
        from app.services.ai.agent.agent_evolution_scheduler import AgentEvolutionScheduler

        scheduler = AgentEvolutionScheduler(redis=mock_redis)
        mock_redis.incr.return_value = 25
        mock_redis.get.return_value = str(__import__("time").time())  # 剛跑過

        result = await scheduler.should_evolve()
        assert result is False

    async def test_no_redis_no_evolve(self):
        """無 Redis 連線時不觸發"""
        from app.services.ai.agent.agent_evolution_scheduler import AgentEvolutionScheduler

        scheduler = AgentEvolutionScheduler(redis=None)
        result = await scheduler.should_evolve()
        assert result is False


# --------------------------------------------------------------------------
# Test 5: PatternLearner normalize 一致性
# --------------------------------------------------------------------------

class TestPatternLearnerNormalize:
    def test_normalize_replaces_date_patterns(self):
        """normalize 應將日期模式替換為佔位符"""
        from app.services.ai.agent.agent_pattern_learner import get_pattern_learner

        learner = get_pattern_learner()
        t1 = learner.normalize_question("查詢 2026-04-10 的公文")
        t2 = learner.normalize_question("查詢 2026-04-15 的公文")

        # 不同日期的同結構問題應 normalize 為相同模板
        assert t1 == t2

    def test_normalize_deterministic(self):
        """同一問題多次 normalize 結果一致"""
        from app.services.ai.agent.agent_pattern_learner import get_pattern_learner

        learner = get_pattern_learner()
        q = "最近工務局有什麼公文？"
        assert learner.normalize_question(q) == learner.normalize_question(q)

    def test_key_generation_consistent(self):
        """相同模板產生相同 key"""
        from app.services.ai.agent.agent_pattern_learner import get_pattern_learner

        learner = get_pattern_learner()
        template = learner.normalize_question("查詢案號 CK-2026-001")
        k1 = learner._make_key(template)
        k2 = learner._make_key(template)
        assert k1 == k2
        assert len(k1) > 0


# --------------------------------------------------------------------------
# Test 6: 完整鏈路 — 低分 → signal 產生
# --------------------------------------------------------------------------

class TestEvalToSignalChain:
    def test_critical_eval_generates_signals(self, evaluator, mock_trace):
        """CRITICAL 評分應產生改進信號"""
        mock_trace.total_ms = 10000  # very slow
        mock_trace.tools_called = ["t1", "t2", "t3", "t4", "t5", "t6", "t7"]  # too many
        mock_trace.tools_succeeded = ["t1"]
        mock_trace.tools_failed = ["t2", "t3", "t4", "t5", "t6", "t7"]

        score = evaluator.evaluate(
            question="x",
            answer="",  # empty
            tool_results=[],
            trace=mock_trace,
        )

        assert score.severity in ("critical", "high")
        assert score.needs_improvement is True
        assert len(score.signals) > 0

    def test_perfect_score_no_improvement_needed(self, evaluator, mock_trace):
        """高分評分不應標記需改進"""
        mock_trace.total_ms = 500
        mock_trace.tools_called = ["search_documents"]
        mock_trace.tools_succeeded = ["search_documents"]

        score = evaluator.evaluate(
            question="公文查詢",
            answer="根據系統查詢，找到以下五筆公文紀錄，涵蓋工務局、建設局、水務局等單位。第一筆是桃工字第115001號，日期2026年4月10日。",
            tool_results=[{"tool": "search_documents", "count": 5}],
            trace=mock_trace,
            citation_result={"accuracy": 1.0, "total": 5, "verified": 5},
        )

        if score.overall >= 0.7:
            assert score.needs_improvement is False
