"""
Agent Conversation Memory — Redis 持久化對話記憶

從 agent_orchestrator.py 提取的對話記憶管理：
- Redis 伺服器端對話歷史儲存
- 自動 TTL 延長
- 連線失敗自動重連 + 靜默降級
- 內容截斷保護
- Session Handoff Protocol：閒置 >30 分鐘自動生成交接摘要

Version: 1.1.0
Created: 2026-03-15
Updated: 2026-04-05 — Session Handoff Protocol
Extracted-from: agent_orchestrator.py v2.5.0
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.ai.ai_config import get_ai_config

logger = logging.getLogger(__name__)

_CONV_TTL = 86400  # 24 小時（延長以保持對話連貫性）
_HANDOFF_TTL = 86400  # 交接摘要 24 小時
_HANDOFF_PREFIX = "session:handoff"
_LAST_MSG_PREFIX = "session:lastmsg"
_IDLE_THRESHOLD_MINUTES = 30


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
        """追加本輪對話並儲存（含內容截斷保護 + 自適應上下文窗口 + DB 持久化）"""
        try:
            r = await self._get_redis()
            if r is None:
                return
            # Track last message time for idle detection
            await self._update_last_message_time(session_id)
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

            # Stage 1A: Persist conversation summary to DB when 4+ turns
            if len(history) >= 8:  # 4+ turns (user+assistant pairs)
                await self._persist_conversation_summary(
                    session_id, question, len(history),
                )
        except Exception as e:
            logger.debug("Conv memory save failed: %s", e)
            self._redis = None

    async def _persist_conversation_summary(
        self,
        session_id: str,
        question: str,
        history_len: int,
    ) -> None:
        """Persist a conversation summary to the agent_learnings table."""
        try:
            import hashlib
            from app.extended.models import AgentLearning
            from app.db.database import AsyncSessionLocal

            turns = history_len // 2
            summary_text = (
                f"Session {session_id}: {turns} turns about "
                f"'{question[:100]}'"
            )
            content_hash = hashlib.md5(
                f"conv_summary:{session_id}".encode(),
            ).hexdigest()

            async with AsyncSessionLocal() as db_session:
                async with db_session.begin():
                    # Check if summary for this session already exists
                    from sqlalchemy import select
                    existing = await db_session.execute(
                        select(AgentLearning.id).where(
                            AgentLearning.content_hash == content_hash,
                            AgentLearning.is_active == True,
                        )
                    )
                    if existing.scalar_one_or_none() is not None:
                        return  # Already persisted

                    learning = AgentLearning(
                        session_id=session_id,
                        learning_type="conversation_summary",
                        content=summary_text,
                        content_hash=content_hash,
                        source_question=question[:200],
                        confidence=0.8,
                    )
                    db_session.add(learning)
        except Exception as e:
            logger.debug("Conversation persistence failed: %s", e)

    # ── Session Handoff Protocol ──

    async def _update_last_message_time(self, session_id: str) -> None:
        """Record the timestamp of the latest message for idle detection."""
        try:
            r = await self._get_redis()
            if r is None:
                return
            now = datetime.now(timezone.utc).isoformat()
            await r.setex(
                f"{_LAST_MSG_PREFIX}:{session_id}",
                _CONV_TTL,
                now,
            )
        except Exception as e:
            logger.debug("Update last message time failed: %s", e)

    async def _get_last_message_time(self, session_id: str) -> Optional[datetime]:
        """Get the timestamp of the last message in this session."""
        try:
            r = await self._get_redis()
            if r is None:
                return None
            raw = await r.get(f"{_LAST_MSG_PREFIX}:{session_id}")
            if raw is None:
                return None
            return datetime.fromisoformat(raw)
        except Exception as e:
            logger.debug("Get last message time failed: %s", e)
            return None

    async def generate_session_handoff(self, session_id: str) -> Optional[dict]:
        """Generate structured handoff when session idles >30 min.

        Uses Gemma 4 to summarize the conversation into a handoff dict:
        {
            "previous_session_id": str,
            "generated_at": ISO timestamp,
            "active_topic": "what was being discussed",
            "key_findings": ["finding1", "finding2"],
            "pending_actions": ["action1", "action2"],
            "context_summary": "2-3 sentence summary",
            "tools_used": ["tool1", "tool2"],
            "last_question": "the user's last question",
        }
        """
        try:
            # Load conversation history
            history = await self.load(session_id)
            if not history or len(history) < 2:
                return None

            # Build conversation text for the LLM
            recent = history[-20:]  # Last 10 turns max
            lines = []
            last_user_question = ""
            for msg in recent:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                lines.append(f"{role}: {content}")
                if role == "user":
                    last_user_question = content

            recent_text = "\n".join(lines)

            prompt = (
                "根據以下對話記錄，生成一份交接摘要 JSON。\n"
                "只回覆 JSON，不要加任何其他文字或 markdown。\n\n"
                f"對話記錄:\n{recent_text}\n\n"
                '回覆格式: {{"active_topic": "正在討論的主題", '
                '"key_findings": ["發現1", "發現2"], '
                '"pending_actions": ["待辦1", "待辦2"], '
                '"context_summary": "2-3句摘要", '
                '"last_question": "用戶最後的問題"}}'
            )

            from app.core.ai_connector import get_ai_connector
            ai = get_ai_connector()
            result = await ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=512,
                prefer_local=True,
                task_type="summary",
            )

            # Parse LLM response
            from app.services.ai.agent_utils import parse_json_safe
            parsed = parse_json_safe(result)
            if not parsed or not isinstance(parsed, dict):
                # Fallback: build a minimal handoff from raw data
                parsed = {
                    "active_topic": "對話交接",
                    "key_findings": [],
                    "pending_actions": [],
                    "context_summary": recent_text[-300:],
                    "last_question": last_user_question,
                }

            handoff = {
                "previous_session_id": session_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "active_topic": parsed.get("active_topic", ""),
                "key_findings": parsed.get("key_findings", []),
                "pending_actions": parsed.get("pending_actions", []),
                "context_summary": parsed.get("context_summary", ""),
                "tools_used": parsed.get("tools_used", []),
                "last_question": parsed.get(
                    "last_question", last_user_question,
                ),
            }

            # Store in Redis
            r = await self._get_redis()
            if r is not None:
                await r.setex(
                    f"{_HANDOFF_PREFIX}:{session_id}",
                    _HANDOFF_TTL,
                    json.dumps(handoff, ensure_ascii=False),
                )
            logger.info(
                "Session handoff generated for %s: topic=%s",
                session_id, handoff.get("active_topic", ""),
            )
            return handoff

        except Exception as e:
            logger.warning("Session handoff generation failed: %s", e)
            return None

    async def get_session_handoff(self, session_id: str) -> Optional[dict]:
        """Retrieve previous session handoff for context injection.

        Called at the start of a new session or after >30min idle.
        Returns the handoff dict if one exists, None otherwise.
        """
        try:
            r = await self._get_redis()
            if r is None:
                return None
            raw = await r.get(f"{_HANDOFF_PREFIX}:{session_id}")
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug("Get session handoff failed: %s", e)
            return None

    async def clear_session_handoff(self, session_id: str) -> None:
        """Clear handoff after it has been consumed by a new session."""
        try:
            r = await self._get_redis()
            if r is None:
                return
            await r.delete(f"{_HANDOFF_PREFIX}:{session_id}")
        except Exception as e:
            logger.debug("Clear session handoff failed: %s", e)

    async def check_and_generate_handoff(self, session_id: str) -> bool:
        """Check if session is idle (>30min since last message).

        If so, generate handoff summary for future resumption.
        Returns True if handoff was generated.
        """
        last_msg_time = await self._get_last_message_time(session_id)
        if not last_msg_time:
            return False
        now = datetime.now(timezone.utc)
        # Ensure both are tz-aware
        if last_msg_time.tzinfo is None:
            last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)
        idle_minutes = (now - last_msg_time).total_seconds() / 60
        if idle_minutes >= _IDLE_THRESHOLD_MINUTES:
            # Check if handoff already exists
            existing = await self.get_session_handoff(session_id)
            if existing:
                return False
            handoff = await self.generate_session_handoff(session_id)
            return handoff is not None
        return False

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
