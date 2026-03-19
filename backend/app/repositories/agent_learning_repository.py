"""
Agent Learning Repository — 學習記錄持久化

Phase 3A: 對標 OpenClaw agent-reflect 永久學習。
將 Memory Flush 提取的學習從 Redis TTL 升級為 DB 持久化。

Version: 1.0.0
Created: 2026-03-15
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.agent_learning import AgentLearning

logger = logging.getLogger(__name__)


class AgentLearningRepository:
    """Agent 學習記錄 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _content_hash(content: str) -> str:
        """計算內容的 MD5 hash（去重用）"""
        return hashlib.md5(content.strip().encode("utf-8")).hexdigest()

    async def save_learnings(
        self,
        session_id: str,
        learnings: List[Dict[str, Any]],
        source_question: Optional[str] = None,
    ) -> int:
        """
        批量保存學習記錄（自動去重 + 強化）。

        Args:
            session_id: 來源 session ID
            learnings: [{"type": "preference|entity|tool_combo", "content": "..."}]
            source_question: 觸發學習的原始問題

        Returns:
            實際新增/更新的記錄數
        """
        count = 0
        try:
            for item in learnings[:20]:  # 上限 20 條
                content = str(item.get("content", "")).strip()
                learning_type = str(item.get("type", "entity")).strip()
                if not content or len(content) < 2:
                    continue

                # 限制 type 範圍
                if learning_type not in ("preference", "entity", "tool_combo", "correction"):
                    learning_type = "entity"

                ch = self._content_hash(content)

                # 檢查是否已存在（去重）
                existing = await self.db.execute(
                    select(AgentLearning).where(
                        and_(
                            AgentLearning.content_hash == ch,
                            AgentLearning.is_active == True,  # noqa: E712
                        )
                    )
                )
                record = existing.scalar_one_or_none()

                if record:
                    # 強化：hit_count + 1
                    record.hit_count += 1
                    count += 1
                else:
                    # 新增
                    new_record = AgentLearning(
                        session_id=session_id,
                        learning_type=learning_type,
                        content=content[:500],
                        content_hash=ch,
                        source_question=source_question[:200] if source_question else None,
                    )
                    self.db.add(new_record)
                    count += 1

            if count > 0:
                await self.db.commit()

            return count

        except Exception as e:
            logger.warning("save_learnings failed: %s", e)
            await self.db.rollback()
            return 0

    async def get_relevant_learnings(
        self,
        question: str,
        learning_type: Optional[str] = None,
        limit: int = 5,
        max_age_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        查詢與問題相關的學習記錄（ILIKE 關鍵字匹配 + 時間範圍）。

        用於注入 planner/synthesizer prompt（Cross-session Learning）。

        Args:
            question: 當前使用者問題（用於關鍵字提取）
            learning_type: 過濾學習類型（None = 不限）
            limit: 最大回傳數量
            max_age_days: 最大學習記錄年齡（天），預設 30 天

        Returns:
            學習記錄清單，依 hit_count DESC, created_at DESC 排序
        """
        try:
            import re
            keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', question)
            if not keywords:
                keywords = re.findall(r'[a-zA-Z]{3,}', question)

            conditions = [AgentLearning.is_active == True]  # noqa: E712

            # 時間範圍篩選：僅取最近 N 天的學習
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            conditions.append(AgentLearning.created_at >= cutoff)

            if learning_type:
                conditions.append(AgentLearning.learning_type == learning_type)

            if keywords:
                kw_filters = [
                    AgentLearning.content.ilike(f"%{kw}%")
                    for kw in keywords[:3]
                ]
                conditions.append(or_(*kw_filters))

            stmt = (
                select(AgentLearning)
                .where(and_(*conditions))
                .order_by(
                    AgentLearning.hit_count.desc(),
                    AgentLearning.created_at.desc(),
                )
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            records = result.scalars().all()

            return [
                {
                    "type": r.learning_type,
                    "content": r.content,
                    "hit_count": r.hit_count,
                    "confidence": r.confidence,
                    "source_question": r.source_question,
                }
                for r in records
            ]

        except Exception as e:
            logger.warning("get_relevant_learnings failed: %s", e)
            return []

    async def get_all_active(
        self,
        learning_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """取得所有啟用的學習記錄（監控/dashboard 用）"""
        try:
            conditions = [AgentLearning.is_active == True]  # noqa: E712
            if learning_type:
                conditions.append(AgentLearning.learning_type == learning_type)

            stmt = (
                select(AgentLearning)
                .where(and_(*conditions))
                .order_by(AgentLearning.hit_count.desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            records = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "type": r.learning_type,
                    "content": r.content,
                    "hit_count": r.hit_count,
                    "confidence": r.confidence,
                    "session_id": r.session_id,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]

        except Exception as e:
            logger.warning("get_all_active failed: %s", e)
            return []

    async def deactivate_learning(self, learning_id: int) -> bool:
        """停用一條學習記錄"""
        try:
            stmt = (
                update(AgentLearning)
                .where(AgentLearning.id == learning_id)
                .values(is_active=False)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.warning("deactivate_learning failed: %s", e)
            await self.db.rollback()
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """取得學習統計"""
        try:
            stmt = (
                select(
                    AgentLearning.learning_type,
                    func.count().label("count"),
                    func.sum(AgentLearning.hit_count).label("total_hits"),
                )
                .where(AgentLearning.is_active == True)  # noqa: E712
                .group_by(AgentLearning.learning_type)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            by_type = {
                r.learning_type: {
                    "count": r.count,
                    "total_hits": r.total_hits or 0,
                }
                for r in rows
            }

            return {
                "total_active": sum(v["count"] for v in by_type.values()),
                "by_type": by_type,
            }

        except Exception as e:
            logger.warning("get_stats failed: %s", e)
            return {"total_active": 0, "by_type": {}}
