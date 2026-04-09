"""
TokenUsageTracker 單元測試

測試 Token 計量追蹤器的本地 fallback 邏輯、預算計算、成本估算。
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.ai.core.token_usage_tracker import (
    TokenUsageTracker,
    DEFAULT_PRICING,
    DEFAULT_DAILY_BUDGET,
)


@pytest.fixture
def tracker():
    t = TokenUsageTracker()
    t._redis = None  # force local fallback
    return t


class TestDefaultPricing:
    def test_ollama_is_free(self):
        assert DEFAULT_PRICING["ollama"]["input"] == 0.0
        assert DEFAULT_PRICING["ollama"]["output"] == 0.0

    def test_groq_has_price(self):
        assert DEFAULT_PRICING["groq"]["input"] > 0

    def test_all_providers_have_both_keys(self):
        for provider, pricing in DEFAULT_PRICING.items():
            assert "input" in pricing, f"{provider} missing input"
            assert "output" in pricing, f"{provider} missing output"


class TestDefaultBudget:
    def test_daily_budget_positive(self):
        assert DEFAULT_DAILY_BUDGET > 0

    def test_daily_budget_reasonable(self):
        assert 100_000 <= DEFAULT_DAILY_BUDGET <= 10_000_000


class TestTrackerInit:
    def test_initial_state(self, tracker):
        assert tracker._redis is None
        assert tracker._local_usage == {}
        assert tracker._alert_sent_today is False


class TestLocalFallback:
    @pytest.mark.asyncio
    async def test_record_and_get_usage(self, tracker):
        await tracker.record(
            provider="ollama",
            model="gemma4",
            feature="chat",
            input_tokens=100,
            output_tokens=50,
        )
        # Local usage should have been recorded
        assert len(tracker._local_usage) > 0

    @pytest.mark.asyncio
    async def test_get_report_empty(self, tracker):
        report = await tracker.get_usage_report()
        assert isinstance(report, dict)


class TestCostEstimation:
    def test_cost_calculation(self):
        # groq: 0.00006 per 1K tokens
        input_tokens = 1000
        price = DEFAULT_PRICING["groq"]["input"]
        cost = (input_tokens / 1000) * price
        assert cost == pytest.approx(0.00006)

    def test_local_model_zero_cost(self):
        input_tokens = 100_000
        price = DEFAULT_PRICING["ollama"]["input"]
        cost = (input_tokens / 1000) * price
        assert cost == 0.0
