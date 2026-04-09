"""
AgentEvolutionScheduler 單元測試
"""

import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.ai.agent.agent_evolution_scheduler import (
    AgentEvolutionScheduler,
    QUERY_COUNTER_KEY,
    LAST_EVOLUTION_KEY,
    SIGNAL_QUEUE_KEY,
    EVOLUTION_STATE_KEY,
)


class TestShouldEvolve:
    @pytest.mark.asyncio
    async def test_no_redis(self):
        scheduler = AgentEvolutionScheduler(redis=None)
        assert await scheduler.should_evolve() is False

    @pytest.mark.asyncio
    async def test_evolve_at_50_queries(self):
        redis = AsyncMock()
        redis.incr.return_value = 50  # 第 50 次
        scheduler = AgentEvolutionScheduler(redis=redis)
        assert await scheduler.should_evolve() is True

    @pytest.mark.asyncio
    async def test_no_evolve_at_49(self):
        redis = AsyncMock()
        redis.incr.return_value = 49
        redis.get.return_value = str(time.time())  # 最近才跑過
        scheduler = AgentEvolutionScheduler(redis=redis)
        assert await scheduler.should_evolve() is False

    @pytest.mark.asyncio
    async def test_evolve_after_24h(self):
        redis = AsyncMock()
        redis.incr.return_value = 3  # 不到 50
        redis.get.return_value = str(time.time() - 90000)  # 超過 24h
        scheduler = AgentEvolutionScheduler(redis=redis)
        assert await scheduler.should_evolve() is True

    @pytest.mark.asyncio
    async def test_first_time_with_data(self):
        redis = AsyncMock()
        redis.incr.return_value = 15  # 超過 10 但從未跑過
        redis.get.return_value = None  # 從未跑過
        scheduler = AgentEvolutionScheduler(redis=redis)
        assert await scheduler.should_evolve() is True


class TestAnalyzeFailurePatterns:
    def test_empty_signals(self):
        scheduler = AgentEvolutionScheduler()
        patterns = scheduler._analyze_failure_patterns([])
        assert patterns == []

    def test_frequent_type(self):
        signals = [
            {"type": "low_relevance", "question_preview": f"q{i}"}
            for i in range(5)
        ]
        scheduler = AgentEvolutionScheduler()
        patterns = scheduler._analyze_failure_patterns(signals)
        assert len(patterns) == 1
        assert patterns[0]["type"] == "low_relevance"
        assert patterns[0]["count"] == 5

    def test_mixed_types(self):
        signals = [
            {"type": "low_relevance"},
            {"type": "low_relevance"},
            {"type": "low_relevance"},
            {"type": "high_latency"},
            {"type": "high_latency"},
        ]
        scheduler = AgentEvolutionScheduler()
        patterns = scheduler._analyze_failure_patterns(signals)
        assert len(patterns) == 1  # 只有 low_relevance >= 3

    def test_below_threshold(self):
        signals = [
            {"type": "a"}, {"type": "a"},  # 只有 2 次
            {"type": "b"},  # 只有 1 次
        ]
        scheduler = AgentEvolutionScheduler()
        patterns = scheduler._analyze_failure_patterns(signals)
        assert len(patterns) == 0  # 都沒到 3 次


class TestEvolution:
    @pytest.mark.asyncio
    async def test_evolve_no_redis(self):
        scheduler = AgentEvolutionScheduler(redis=None)
        result = await scheduler.evolve()
        assert result["status"] == "skip"

    @pytest.mark.asyncio
    async def test_evolve_with_signals(self):
        redis = AsyncMock()

        # Mock signal queue
        signals = [
            json.dumps({"type": "low_relevance", "question_preview": "q1"}),
            json.dumps({"type": "low_relevance", "question_preview": "q2"}),
            json.dumps({"type": "low_relevance", "question_preview": "q3"}),
        ]
        call_count = 0

        async def mock_rpop(key):
            nonlocal call_count
            if call_count < len(signals):
                val = signals[call_count]
                call_count += 1
                return val
            return None

        redis.rpop = mock_rpop
        redis.zrevrange.return_value = []
        redis.zrange.return_value = []
        redis.lrange.return_value = []
        redis.zrangebyscore.return_value = []

        scheduler = AgentEvolutionScheduler(redis=redis)
        result = await scheduler.evolve()

        assert result["signals_consumed"] == 3
        assert len(result["failure_patterns"]) == 1
        assert result["failure_patterns"][0]["type"] == "low_relevance"

    @pytest.mark.asyncio
    async def test_compute_quality_trend_insufficient(self):
        redis = AsyncMock()
        redis.lrange.return_value = [json.dumps({"overall": 0.8})] * 3
        scheduler = AgentEvolutionScheduler(redis=redis)
        trend = await scheduler._compute_quality_trend()
        assert trend["status"] == "insufficient_data"

    @pytest.mark.asyncio
    async def test_compute_quality_trend_improving(self):
        redis = AsyncMock()
        # Newest first (list head)
        recent = [json.dumps({"overall": 0.9})] * 5  # 最近高分
        older = [json.dumps({"overall": 0.6})] * 5   # 之前低分
        redis.lrange.return_value = recent + older
        scheduler = AgentEvolutionScheduler(redis=redis)
        trend = await scheduler._compute_quality_trend()
        assert trend["direction"] == "improving"
        assert trend["slope"] > 0

    @pytest.mark.asyncio
    async def test_compute_quality_trend_declining(self):
        redis = AsyncMock()
        recent = [json.dumps({"overall": 0.4})] * 5  # 最近低分
        older = [json.dumps({"overall": 0.8})] * 5   # 之前高分
        redis.lrange.return_value = recent + older
        scheduler = AgentEvolutionScheduler(redis=redis)
        trend = await scheduler._compute_quality_trend()
        assert trend["direction"] == "declining"

    @pytest.mark.asyncio
    async def test_get_evolution_status_never_run(self):
        redis = AsyncMock()
        redis.get.return_value = None
        scheduler = AgentEvolutionScheduler(redis=redis)
        status = await scheduler.get_evolution_status()
        assert status["status"] == "never_run"

    @pytest.mark.asyncio
    async def test_cleanup_stale_patterns(self):
        redis = AsyncMock()
        redis.zrangebyscore.return_value = [
            (b"pattern_abc", 0.001),  # 分數極低 → 應清理
            (b"pattern_xyz", 5.0),    # 分數正常 → 保留
        ]
        scheduler = AgentEvolutionScheduler(redis=redis)
        cleaned = await scheduler._cleanup_stale_learnings()
        assert cleaned == 1
        redis.zrem.assert_called_once()
