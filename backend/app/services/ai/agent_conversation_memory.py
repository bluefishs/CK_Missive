"""
Agent Conversation Memory — Redis 持久化對話記憶

從 agent_orchestrator.py 提取的對話記憶管理：
- Redis 伺服器端對話歷史儲存
- 自動 TTL 延長
- 連線失敗自動重連 + 靜默降級
- 內容截斷保護

Version: 1.0.0
Created: 2026-03-15
Extracted-from: agent_orchestrator.py v2.5.0
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.services.ai.ai_config import get_ai_config

logger = logging.getLogger(__name__)

_CONV_TTL = 3600  # 1 小時


class ConversationMemory:
    """
    伺服器端對話記憶 — Redis 持久化

    Key 格式: agent:conv:{session_id}
    Value: JSON array of {role, content}
    TTL: 1 小時（每次存取自動延長）

    設計原則:
    - Redis 不可用時靜默降級（不影響問答流程）
    - 僅儲存 user/assistant 文字，不存工具中間結果
    - 與前端傳入 history 互斥：有 session_id 用 Redis，否則用 request body
    - max_turns 從 ai_config.rag_max_history_turns 讀取（SSOT）
    - 連線失敗後自動重連（避免一次錯誤永久降級）
    """

    _PREFIX = "agent:conv"
    _MAX_CONTENT_CHARS = 1000  # 每則訊息內容截斷上限

    def __init__(self) -> None:
        self._redis = None

    async def _get_redis(self):
        """取得 Redis 連線，失敗時重試一次（避免暫時斷線永久降級）"""
        if self._redis is not None:
            try:
                await self._redis.ping()
                return self._redis
            except Exception:
                self._redis = None

        try:
            from app.core.redis_client import get_redis
            self._redis = await get_redis()
            return self._redis
        except Exception:
            return None

    async def load(self, session_id: str) -> List[Dict[str, str]]:
        """載入對話歷史"""
        try:
            r = await self._get_redis()
            if r is None:
                return []
            raw = await r.get(f"{self._PREFIX}:{session_id}")
            if raw is None:
                return []
            # 延長 TTL
            await r.expire(f"{self._PREFIX}:{session_id}", _CONV_TTL)
            return json.loads(raw)
        except Exception as e:
            logger.debug("Conv memory load failed: %s", e)
            self._redis = None
            return []

    def _estimate_query_complexity(
        self, query: str, tool_count: int = 0,
    ) -> str:
        """
        Estimate query complexity: simple / medium / complex.

        Uses configurable thresholds from ai_config:
        - simple: short query AND no tools expected
        - complex: long query OR multiple tools
        - medium: everything else (default)
        """
        config = get_ai_config()
        query_len = len(query)

        # Simple: short query with no tools
        if query_len < config.adaptive_context_query_short and tool_count <= 0:
            return "simple"
        # Complex: long query or many tools
        if (
            tool_count >= config.adaptive_context_tool_complex
            or query_len > config.adaptive_context_query_long
        ):
            return "complex"
        return "medium"

    def _get_adaptive_max_turns(self, complexity: str) -> int:
        """
        Get context window size based on query complexity.

        Falls back to rag_max_history_turns when adaptive context is disabled.
        """
        config = get_ai_config()
        if not config.adaptive_context_enabled:
            return config.rag_max_history_turns
        return {
            "simple": config.adaptive_context_simple,
            "medium": config.adaptive_context_medium,
            "complex": config.adaptive_context_complex,
        }.get(complexity, config.rag_max_history_turns)

    async def save(
        self,
        session_id: str,
        question: str,
        answer: str,
        existing_history: List[Dict[str, str]],
        *,
        tool_count: int = 0,
    ) -> None:
        """追加本輪對話並儲存（含內容截斷保護 + 自適應上下文窗口）"""
        try:
            r = await self._get_redis()
            if r is None:
                return
            history = list(existing_history)
            # 截斷過長的使用者問題和回答，避免 Redis 記憶體膨脹
            history.append({
                "role": "user",
                "content": question[:self._MAX_CONTENT_CHARS],
            })
            if answer:
                history.append({
                    "role": "assistant",
                    "content": answer[:self._MAX_CONTENT_CHARS],
                })
            # 自適應上下文窗口：根據查詢複雜度動態調整保留輪數
            complexity = self._estimate_query_complexity(question, tool_count)
            max_turns = self._get_adaptive_max_turns(complexity)
            logger.debug(
                "Adaptive context: complexity=%s, max_turns=%d, tool_count=%d, query_len=%d",
                complexity, max_turns, tool_count, len(question),
            )
            history = history[-(max_turns * 2):]
            await r.setex(
                f"{self._PREFIX}:{session_id}",
                _CONV_TTL,
                json.dumps(history, ensure_ascii=False),
            )
        except Exception as e:
            logger.debug("Conv memory save failed: %s", e)
            self._redis = None

    async def delete(self, session_id: str) -> None:
        """清除對話歷史"""
        try:
            r = await self._get_redis()
            if r is None:
                return
            await r.delete(f"{self._PREFIX}:{session_id}")
        except Exception as e:
            logger.debug("Conv memory delete failed: %s", e)
            self._redis = None


# 單例
_conversation_memory: Optional[ConversationMemory] = None


def get_conversation_memory() -> ConversationMemory:
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory
