"""
Agent Conversation Summarizer — 長對話摘要壓縮

3-Tier Adaptive Compaction：
- Tier 1: 完整 LLM 摘要（Full）
- Tier 2: 部分摘要（跳過超長訊息）
- Tier 3: 元數據降級（純規則，無 LLM）

Phase 3A 升級：
- 學習雙寫：Redis（快取）+ PostgreSQL（永久保存）
- 3-Tier 降級壓縮策略
- 持久化學習注入 effective_history

Version: 2.0.0
Created: 2026-03-14
Updated: 2026-03-15 - v2.0.0 3-Tier Compaction + DB 持久化
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """將以下對話歷史壓縮為一段繁體中文摘要（最多{max_chars}字）。

規則：
- 保留：使用者關心的主題、已查詢過的內容、重要的查詢結果
- 忽略：問候語、重複查詢、無關閒聊
- 格式：簡潔的要點列表

{existing_summary}

對話歷史：
{history_text}

請直接輸出摘要，不需要標題或前綴："""


class ConversationSummarizer:
    """長對話摘要壓縮（3-Tier Adaptive Compaction）"""

    _PREFIX = "agent:conv_summary"
    _TTL = 3600  # 1 小時

    def __init__(
        self,
        trigger_turns: int = 6,
        max_chars: int = 500,
        keep_recent: int = 2,
    ):
        self._trigger_turns = trigger_turns
        self._max_chars = max_chars
        self._keep_recent = keep_recent
        self._redis = None

    async def _get_redis(self):
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

    def should_summarize(self, history: List[Dict[str, str]]) -> bool:
        """判斷是否需要觸發摘要"""
        turns = len(history) // 2
        return turns >= self._trigger_turns

    async def get_effective_history(
        self,
        session_id: str,
        history: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """
        取得有效歷史：摘要 + 學習 + 最近 N 輪原文。

        如果不需要摘要或 Redis 不可用，回傳原始歷史。
        """
        if not self.should_summarize(history):
            return history

        redis = await self._get_redis()
        if not redis:
            keep = self._keep_recent * 2
            return history[-keep:] if len(history) > keep else history

        try:
            summary_key = f"{self._PREFIX}:{session_id}"
            summary = await redis.get(summary_key)

            if summary:
                summary_text = (
                    summary.decode() if isinstance(summary, bytes) else summary
                )

                # Phase 2D/3A: 載入學習資料（Redis → DB fallback）
                learnings_text = await self._load_learnings(session_id, redis)

                prefix = f"先前對話摘要：{summary_text}"
                if learnings_text:
                    prefix = f"先前學習：{learnings_text}\n\n{prefix}"

                keep = self._keep_recent * 2
                recent = history[-keep:] if len(history) > keep else history
                return [
                    {"role": "system", "content": prefix},
                    *recent,
                ]
            else:
                keep = self._keep_recent * 2
                return history[-keep:] if len(history) > keep else history

        except Exception as e:
            logger.debug("Summarizer.get_effective_history failed: %s", e)
            keep = self._keep_recent * 2
            return history[-keep:] if len(history) > keep else history

    async def _load_learnings(self, session_id: str, redis) -> str:
        """載入學習資料：Redis 快取 → DB 持久化 fallback"""
        try:
            # 1. Redis 快取（快速路徑）
            learnings_key = f"agent:learnings:{session_id}"
            cached = await redis.get(learnings_key)
            if cached:
                return cached.decode() if isinstance(cached, bytes) else cached

            # 2. DB 持久化 fallback（Phase 3A）
            from app.services.ai.core.ai_config import get_ai_config
            config = get_ai_config()
            if not config.learning_persist_enabled:
                return ""

            try:
                from app.db.database import AsyncSessionLocal
                from app.repositories.agent_learning_repository import AgentLearningRepository

                async with AsyncSessionLocal() as db:
                    repo = AgentLearningRepository(db)
                    # 取得全域高頻學習（不限 session）
                    learnings = await repo.get_all_active(limit=config.learning_inject_limit)
                    if learnings:
                        items = [f"- [{l['type']}] {l['content']}" for l in learnings]
                        return "\n".join(items)
            except Exception:
                pass

            return ""
        except Exception:
            return ""

    async def extract_and_flush_learnings(
        self,
        session_id: str,
        history: List[Dict[str, str]],
        ai_connector: Any,
        db: Any = None,
    ) -> None:
        """
        Phase 2D/3A: 壓縮前提取學習。

        雙寫策略：
        - Redis: 快取（24h TTL，快速讀取）
        - PostgreSQL: 永久保存（Phase 3A 新增，跨 session 累積）
        """
        redis = await self._get_redis()
        if not redis:
            return

        try:
            from app.services.ai.core.ai_config import get_ai_config
            config = get_ai_config()
            if not config.memory_flush_enabled:
                return

            history_text = "\n".join(
                f"{'使用者' if m.get('role') == 'user' else 'AI'}: "
                f"{m.get('content', '')[:150]}"
                for m in history[-12:]
            )

            prompt = (
                f"從以下對話中提取關鍵學習點（JSON 格式，最多{config.memory_flush_max_learnings}條）：\n\n"
                f"{history_text}\n\n"
                f"提取重點：使用者偏好的查詢模式、常用的實體/機關名稱、成功的工具組合。\n"
                f'回傳 JSON：{{"learnings": [{{"type": "preference|entity|tool_combo", "content": "..."}}]}}'
            )

            response = await ai_connector.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=256,
                task_type="chat",
                response_format={"type": "json_object"},
            )

            if response:
                response_text = response.strip()[:1000]

                # 1. Redis 快取寫入
                learnings_key = f"agent:learnings:{session_id}"
                await redis.set(
                    learnings_key,
                    response_text,
                    ex=config.memory_flush_learnings_ttl,
                )

                # 2. DB 持久化寫入（Phase 3A 新增）
                if config.learning_persist_enabled:
                    await self._persist_learnings_to_db(
                        session_id, response_text, history, db,
                    )

                logger.info("Memory flush: learnings saved for session %s", session_id)

        except Exception as e:
            logger.debug("extract_and_flush_learnings failed: %s", e)

    async def _persist_learnings_to_db(
        self,
        session_id: str,
        response_text: str,
        history: List[Dict[str, str]],
        db: Any = None,
    ) -> None:
        """將學習記錄持久化至 PostgreSQL"""
        try:
            parsed = json.loads(response_text)
            learnings = parsed.get("learnings", [])
            if not learnings:
                return

            # 提取原始問題
            source_question = None
            for m in reversed(history):
                if m.get("role") == "user":
                    source_question = m.get("content", "")[:200]
                    break

            if db:
                from app.repositories.agent_learning_repository import AgentLearningRepository
                repo = AgentLearningRepository(db)
                await repo.save_learnings(session_id, learnings, source_question)
            else:
                from app.db.database import AsyncSessionLocal
                from app.repositories.agent_learning_repository import AgentLearningRepository
                async with AsyncSessionLocal() as new_db:
                    repo = AgentLearningRepository(new_db)
                    await repo.save_learnings(session_id, learnings, source_question)

        except (json.JSONDecodeError, Exception) as e:
            logger.debug("_persist_learnings_to_db failed: %s", e)

    async def summarize_and_store(
        self,
        session_id: str,
        history: List[Dict[str, str]],
        ai_connector: Any,
        db: Any = None,
    ) -> None:
        """
        3-Tier Adaptive Compaction + 學習提取 + 摘要儲存。

        Tier 1: 完整 LLM 摘要
        Tier 2: 部分摘要（跳過超長訊息）
        Tier 3: 元數據降級（純規則提取，無 LLM）
        """
        if not self.should_summarize(history):
            return

        # Phase 2D/3A: 壓縮前提取學習
        await self.extract_and_flush_learnings(session_id, history, ai_connector, db)

        redis = await self._get_redis()
        if not redis:
            return

        from app.services.ai.core.ai_config import get_ai_config
        config = get_ai_config()

        summary_key = f"{self._PREFIX}:{session_id}"
        tier_key = f"{self._PREFIX}:{session_id}:tier"

        # 載入現有摘要
        existing = await redis.get(summary_key)
        existing_text = ""
        if existing:
            existing_text = (
                f"現有摘要：{existing.decode() if isinstance(existing, bytes) else existing}\n\n"
            )

        keep = self._keep_recent * 2
        to_summarize = history[:-keep] if len(history) > keep else history

        # ── Tier 1: 完整 LLM 摘要 ──
        summary = await self._tier1_full_summary(
            to_summarize, existing_text, ai_connector, config,
        )
        if summary:
            await redis.set(summary_key, summary, ex=self._TTL)
            await redis.set(tier_key, "1", ex=self._TTL)
            logger.info("Tier 1 summary: %s (%d chars)", session_id, len(summary))
            return

        # ── Tier 2: 部分摘要（跳過超長訊息）──
        summary = await self._tier2_partial_summary(
            to_summarize, existing_text, ai_connector, config,
        )
        if summary:
            await redis.set(summary_key, summary, ex=self._TTL)
            await redis.set(tier_key, "2", ex=self._TTL)
            logger.info("Tier 2 summary: %s (%d chars)", session_id, len(summary))
            return

        # ── Tier 3: 元數據降級（純規則）──
        metadata = self._tier3_metadata_only(to_summarize, config)
        await redis.set(summary_key, metadata, ex=self._TTL)
        await redis.set(tier_key, "3", ex=self._TTL)
        logger.info("Tier 3 metadata fallback: %s", session_id)

    async def _tier1_full_summary(
        self,
        messages: List[Dict[str, str]],
        existing_text: str,
        ai_connector: Any,
        config: Any,
    ) -> Optional[str]:
        """Tier 1: 完整 LLM 摘要"""
        try:
            history_text = "\n".join(
                f"{'使用者' if m.get('role') == 'user' else 'AI'}: "
                f"{m.get('content', '')[:200]}"
                for m in messages
            )

            prompt = _SUMMARIZE_PROMPT.format(
                max_chars=self._max_chars,
                existing_summary=existing_text,
                history_text=history_text,
            )

            summary = await asyncio.wait_for(
                ai_connector.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=256,
                ),
                timeout=config.compaction_tier1_timeout,
            )

            if summary:
                return summary.strip()[:self._max_chars]
            return None

        except (asyncio.TimeoutError, Exception) as e:
            logger.debug("Tier 1 summary failed: %s", e)
            return None

    async def _tier2_partial_summary(
        self,
        messages: List[Dict[str, str]],
        existing_text: str,
        ai_connector: Any,
        config: Any,
    ) -> Optional[str]:
        """Tier 2: 部分摘要 — 跳過超長訊息"""
        try:
            max_msg_chars = config.compaction_tier2_max_msg_chars
            filtered = [
                m for m in messages
                if len(m.get("content", "")) <= max_msg_chars
            ]

            if not filtered:
                return None

            history_text = "\n".join(
                f"{'使用者' if m.get('role') == 'user' else 'AI'}: "
                f"{m.get('content', '')[:150]}"
                for m in filtered
            )

            skipped = len(messages) - len(filtered)
            note = f"（略過 {skipped} 條超長訊息）\n" if skipped else ""

            prompt = _SUMMARIZE_PROMPT.format(
                max_chars=self._max_chars,
                existing_summary=existing_text + note,
                history_text=history_text,
            )

            summary = await asyncio.wait_for(
                ai_connector.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=256,
                ),
                timeout=config.compaction_tier1_timeout,
            )

            if summary:
                return summary.strip()[:self._max_chars]
            return None

        except (asyncio.TimeoutError, Exception) as e:
            logger.debug("Tier 2 summary failed: %s", e)
            return None

    def _tier3_metadata_only(
        self,
        messages: List[Dict[str, str]],
        config: Any,
    ) -> str:
        """Tier 3: 元數據降級 — 純規則提取，無 LLM"""
        user_msgs = [m for m in messages if m.get("role") == "user"]
        ai_msgs = [m for m in messages if m.get("role") != "user"]

        # 提取主題（中文名詞 2-4 字）
        all_text = " ".join(m.get("content", "") for m in user_msgs)
        topics = list(dict.fromkeys(
            re.findall(r'[\u4e00-\u9fff]{2,4}', all_text)
        ))[:config.compaction_tier3_topic_limit]

        metadata = {
            "tier": 3,
            "turns": len(user_msgs),
            "topics": topics,
            "last_question": user_msgs[-1].get("content", "")[:100] if user_msgs else "",
        }

        return json.dumps(metadata, ensure_ascii=False)


# ── Singleton ──

_summarizer: Optional[ConversationSummarizer] = None


def get_summarizer() -> ConversationSummarizer:
    """取得 ConversationSummarizer 單例"""
    global _summarizer
    if _summarizer is None:
        from app.services.ai.core.ai_config import get_ai_config

        config = get_ai_config()
        _summarizer = ConversationSummarizer(
            trigger_turns=config.conv_summary_trigger_turns,
            max_chars=config.conv_summary_max_chars,
            keep_recent=config.conv_summary_keep_recent,
        )
    return _summarizer
