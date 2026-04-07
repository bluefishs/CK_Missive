"""
ConversationMemory 單元測試

測試範圍：
- Redis 連線管理（靜默降級）
- 對話歷史 load / save / delete
- 內容截斷保護
- 最大輪數截斷
- 單例工廠函數

共 15 test cases
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.agent_conversation_memory import (
    ConversationMemory,
    get_conversation_memory,
    _CONV_TTL,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def memory():
    """Fresh ConversationMemory instance with no Redis."""
    m = ConversationMemory()
    return m


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    r = AsyncMock()
    r.ping = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.setex = AsyncMock()
    r.expire = AsyncMock()
    r.delete = AsyncMock()
    return r


@pytest.fixture
def memory_with_redis(memory, mock_redis):
    """ConversationMemory with pre-injected Redis."""
    memory._redis = mock_redis
    return memory


# ============================================================================
# Redis 連線管理
# ============================================================================

class TestRedisConnection:
    """Redis 連線與降級測試"""

    @pytest.mark.asyncio
    async def test_no_redis_load_returns_empty(self, memory):
        """Redis 不可用時 load 返回空陣列"""
        memory._get_redis = AsyncMock(return_value=None)
        result = await memory.load("test-session")
        assert result == []

    @pytest.mark.asyncio
    async def test_no_redis_save_does_not_raise(self, memory):
        """Redis 不可用時 save 不應拋出異常"""
        memory._get_redis = AsyncMock(return_value=None)
        await memory.save("test-session", "問題", "回答", [])

    @pytest.mark.asyncio
    async def test_no_redis_delete_does_not_raise(self, memory):
        """Redis 不可用時 delete 不應拋出異常"""
        memory._get_redis = AsyncMock(return_value=None)
        await memory.delete("test-session")

    @pytest.mark.asyncio
    async def test_redis_error_resets_connection(self, memory_with_redis, mock_redis):
        """Redis 操作失敗時重置連線"""
        mock_redis.get.side_effect = Exception("Connection lost")
        result = await memory_with_redis.load("session-1")
        assert result == []
        assert memory_with_redis._redis is None


# ============================================================================
# Load
# ============================================================================

class TestLoad:
    """對話歷史載入測試"""

    @pytest.mark.asyncio
    async def test_load_empty_session(self, memory_with_redis, mock_redis):
        """空 session 返回空陣列"""
        mock_redis.get.return_value = None
        result = await memory_with_redis.load("new-session")
        assert result == []

    @pytest.mark.asyncio
    async def test_load_existing_session(self, memory_with_redis, mock_redis):
        """載入已有的對話歷史"""
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好！"},
        ]
        mock_redis.get.return_value = json.dumps(history, ensure_ascii=False)
        result = await memory_with_redis.load("existing-session")
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "你好"

    @pytest.mark.asyncio
    async def test_load_extends_ttl(self, memory_with_redis, mock_redis):
        """載入時自動延長 TTL"""
        mock_redis.get.return_value = json.dumps([{"role": "user", "content": "test"}])
        await memory_with_redis.load("session-ttl")
        mock_redis.expire.assert_called_once_with("agent:conv:session-ttl", _CONV_TTL)


# ============================================================================
# Save
# ============================================================================

class TestSave:
    """對話歷史儲存測試"""

    @pytest.mark.asyncio
    async def test_save_appends_messages(self, memory_with_redis, mock_redis):
        """儲存時追加 user + assistant 訊息"""
        await memory_with_redis.save("session-1", "問題", "回答", [])
        # setex called twice: once for last_message_time, once for conversation
        assert mock_redis.setex.call_count == 2
        # Last call is the conversation save
        args = mock_redis.setex.call_args_list[-1]
        saved = json.loads(args[0][2])
        assert len(saved) == 2
        assert saved[0]["role"] == "user"
        assert saved[0]["content"] == "問題"
        assert saved[1]["role"] == "assistant"
        assert saved[1]["content"] == "回答"

    @pytest.mark.asyncio
    async def test_save_truncates_long_content(self, memory_with_redis, mock_redis):
        """超長內容被截斷至 _MAX_CONTENT_CHARS"""
        long_text = "x" * 2000
        await memory_with_redis.save("session-trunc", long_text, long_text, [])
        args = mock_redis.setex.call_args
        saved = json.loads(args[0][2])
        assert len(saved[0]["content"]) == 1000
        assert len(saved[1]["content"]) == 1000

    @pytest.mark.asyncio
    async def test_save_respects_max_turns(self, memory_with_redis, mock_redis):
        """超過 max_turns 時截斷歷史（adaptive disabled → 使用 rag_max_history_turns）"""
        existing = []
        for i in range(20):
            existing.append({"role": "user", "content": f"q{i}"})
            existing.append({"role": "assistant", "content": f"a{i}"})

        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mock_config:
            cfg = MagicMock()
            cfg.rag_max_history_turns = 5
            cfg.adaptive_context_enabled = False  # 停用自適應
            cfg.adaptive_context_query_short = 20
            cfg.adaptive_context_query_long = 100
            cfg.adaptive_context_tool_complex = 3
            mock_config.return_value = cfg
            await memory_with_redis.save("session-max", "new_q", "new_a", existing)

        args = mock_redis.setex.call_args
        saved = json.loads(args[0][2])
        # max_turns=5 → keep last 10 messages (5*2)
        assert len(saved) == 10

    @pytest.mark.asyncio
    async def test_save_empty_answer_skipped(self, memory_with_redis, mock_redis):
        """空回答不儲存 assistant 訊息"""
        await memory_with_redis.save("session-empty", "問題", "", [])
        args = mock_redis.setex.call_args
        saved = json.loads(args[0][2])
        assert len(saved) == 1
        assert saved[0]["role"] == "user"


# ============================================================================
# Adaptive Context Window
# ============================================================================

class TestAdaptiveContextWindow:
    """自適應上下文窗口測試"""

    def _make_config(self, **overrides):
        """建立帶有預設自適應參數的 mock config"""
        cfg = MagicMock()
        cfg.rag_max_history_turns = 4
        cfg.adaptive_context_enabled = True
        cfg.adaptive_context_simple = 2
        cfg.adaptive_context_medium = 4
        cfg.adaptive_context_complex = 6
        cfg.adaptive_context_query_short = 20
        cfg.adaptive_context_query_long = 100
        cfg.adaptive_context_tool_complex = 3
        for k, v in overrides.items():
            setattr(cfg, k, v)
        return cfg

    def test_simple_query_classification(self, memory):
        """短查詢 + 無工具 → simple"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            result = memory._estimate_query_complexity("你好", tool_count=0)
        assert result == "simple"

    def test_medium_query_classification(self, memory):
        """中等長度查詢 + 少量工具 → medium"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            result = memory._estimate_query_complexity("請查詢今年三月的公文統計資料", tool_count=1)
        assert result == "medium"

    def test_complex_query_by_tool_count(self, memory):
        """多工具 → complex"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            result = memory._estimate_query_complexity("查詢", tool_count=3)
        assert result == "complex"

    def test_complex_query_by_length(self, memory):
        """長查詢 → complex"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            long_query = "x" * 101  # 超過 adaptive_context_query_long (100)
            result = memory._estimate_query_complexity(long_query, tool_count=0)
        assert result == "complex"

    def test_adaptive_max_turns_simple(self, memory):
        """simple → 2 turns"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            assert memory._get_adaptive_max_turns("simple") == 2

    def test_adaptive_max_turns_complex(self, memory):
        """complex → 6 turns"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            assert memory._get_adaptive_max_turns("complex") == 6

    def test_adaptive_disabled_falls_back(self, memory):
        """adaptive 停用時 → 使用 rag_max_history_turns"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config(adaptive_context_enabled=False)
            assert memory._get_adaptive_max_turns("simple") == 4
            assert memory._get_adaptive_max_turns("complex") == 4

    def test_unknown_complexity_falls_back(self, memory):
        """未知複雜度 → 使用 rag_max_history_turns"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            assert memory._get_adaptive_max_turns("unknown") == 4

    @pytest.mark.asyncio
    async def test_save_uses_adaptive_simple(self, memory_with_redis, mock_redis):
        """save 使用 adaptive: short query → simple → 2 turns (keep 4 messages)"""
        existing = []
        for i in range(10):
            existing.append({"role": "user", "content": f"q{i}"})
            existing.append({"role": "assistant", "content": f"a{i}"})

        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            await memory_with_redis.save("s1", "hi", "hello", existing, tool_count=0)

        saved = json.loads(mock_redis.setex.call_args[0][2])
        # simple: max_turns=2 → keep last 4 messages (2*2)
        assert len(saved) == 4

    @pytest.mark.asyncio
    async def test_save_uses_adaptive_complex(self, memory_with_redis, mock_redis):
        """save 使用 adaptive: many tools → complex → 6 turns (keep 12 messages)"""
        existing = []
        for i in range(10):
            existing.append({"role": "user", "content": f"q{i}"})
            existing.append({"role": "assistant", "content": f"a{i}"})

        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            await memory_with_redis.save(
                "s2", "請分析所有公文", "結果...", existing, tool_count=5,
            )

        saved = json.loads(mock_redis.setex.call_args[0][2])
        # complex: max_turns=6 → keep last 12 messages (6*2)
        assert len(saved) == 12

    @pytest.mark.asyncio
    async def test_save_tool_count_keyword_only(self, memory_with_redis, mock_redis):
        """tool_count 為 keyword-only 參數，不傳時預設 0"""
        with patch("app.services.ai.agent_conversation_memory.get_ai_config") as mc:
            mc.return_value = self._make_config()
            # 不傳 tool_count → 預設 0
            await memory_with_redis.save("s3", "hi", "hey", [])
        # 不應拋出異常; setex called twice (last_message_time + conversation)
        assert mock_redis.setex.call_count == 2


# ============================================================================
# Delete
# ============================================================================

class TestDelete:
    """對話歷史刪除測試"""

    @pytest.mark.asyncio
    async def test_delete_session(self, memory_with_redis, mock_redis):
        """刪除 session"""
        await memory_with_redis.delete("session-del")
        mock_redis.delete.assert_called_once_with("agent:conv:session-del")


# ============================================================================
# 單例工廠
# ============================================================================

class TestSingleton:
    """單例模式測試"""

    def test_get_conversation_memory_returns_same_instance(self):
        """get_conversation_memory 返回同一實例"""
        import app.services.ai.agent_conversation_memory as mod
        mod._conversation_memory = None  # reset
        m1 = get_conversation_memory()
        m2 = get_conversation_memory()
        assert m1 is m2
        mod._conversation_memory = None  # cleanup
