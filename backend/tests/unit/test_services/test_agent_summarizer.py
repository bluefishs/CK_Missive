"""
ConversationSummarizer 單元測試

測試對話摘要邏輯（不依賴 Redis/LLM）:
- 觸發條件判斷
- 有效歷史截斷
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.ai.agent_summarizer import ConversationSummarizer


def _make_history(turns: int) -> list:
    """建構 N 輪對話歷史"""
    history = []
    for i in range(turns):
        history.append({"role": "user", "content": f"問題 {i+1}"})
        history.append({"role": "assistant", "content": f"回答 {i+1}"})
    return history


class TestShouldSummarize:
    """摘要觸發條件"""

    def test_below_threshold_no_trigger(self):
        summarizer = ConversationSummarizer(trigger_turns=6)
        history = _make_history(5)
        assert summarizer.should_summarize(history) is False

    def test_at_threshold_triggers(self):
        summarizer = ConversationSummarizer(trigger_turns=6)
        history = _make_history(6)
        assert summarizer.should_summarize(history) is True

    def test_above_threshold_triggers(self):
        summarizer = ConversationSummarizer(trigger_turns=6)
        history = _make_history(10)
        assert summarizer.should_summarize(history) is True

    def test_empty_history_no_trigger(self):
        summarizer = ConversationSummarizer(trigger_turns=6)
        assert summarizer.should_summarize([]) is False

    def test_custom_threshold(self):
        summarizer = ConversationSummarizer(trigger_turns=3)
        history = _make_history(3)
        assert summarizer.should_summarize(history) is True


class TestGetEffectiveHistory:
    """有效歷史截斷"""

    @pytest.mark.asyncio
    async def test_short_history_unchanged(self):
        summarizer = ConversationSummarizer(trigger_turns=6)
        history = _make_history(3)
        result = await summarizer.get_effective_history("test_session", history)
        assert result == history

    @pytest.mark.asyncio
    async def test_long_history_truncated_no_redis(self):
        """無 Redis 時截斷至最近 N 輪"""
        summarizer = ConversationSummarizer(trigger_turns=6, keep_recent=2)
        history = _make_history(10)
        result = await summarizer.get_effective_history("test_session", history)
        # 20 messages → keep last 4 (2 turns)
        assert len(result) == 4
        assert result[0]["content"] == "問題 9"
        assert result[-1]["content"] == "回答 10"

    @pytest.mark.asyncio
    async def test_summarize_and_store_no_redis(self):
        """無 Redis 時不報錯 (mock 外部依賴避免全量測試 flaky)"""
        summarizer = ConversationSummarizer(trigger_turns=6)
        history = _make_history(10)
        # Mock Redis 和 learning 持久化，避免全量測試時受其他模組影響
        with patch.object(summarizer, "_get_redis", AsyncMock(return_value=None)), \
             patch.object(summarizer, "extract_and_flush_learnings", AsyncMock()):
            await summarizer.summarize_and_store("test_session", history, None)


class TestSummarizerInit:
    """初始化參數"""

    def test_default_values(self):
        summarizer = ConversationSummarizer()
        assert summarizer._trigger_turns == 6
        assert summarizer._max_chars == 500
        assert summarizer._keep_recent == 2

    def test_custom_values(self):
        summarizer = ConversationSummarizer(
            trigger_turns=4, max_chars=300, keep_recent=3,
        )
        assert summarizer._trigger_turns == 4
        assert summarizer._max_chars == 300
        assert summarizer._keep_recent == 3
