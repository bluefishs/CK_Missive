"""
Agent Learning Repository — 學習記錄持久化

Phase 3A: 持久化學習記錄。
將 Memory Flush 提取的學習從 Redis TTL 升級為 DB 持久化。

Version: 1.0.0
Created: 2026-03-15
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
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

            # Graduated patterns are already internalized -> exclude them
            # to reduce noise. Chronic patterns are surfaced for review.
            conditions.append(
                AgentLearning.graduation_status.in_(["active", "chronic"])
            )

            stmt = (
                select(AgentLearning)
                .where(and_(*conditions))
                .order_by(
                    # Surface chronic patterns first (need manual review)
                    sa.case(
                        (AgentLearning.graduation_status == "chronic", 0),
                        else_=1,
                    ),
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
                    "graduation_status": r.graduation_status or "active",
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
        """
        Learning 統計摘要。

        Returns:
            {
                total: int, active: int, graduated: int, chronic: int,
                by_type: {preference: N, entity: N, ...},
                total_hits: int,
            }
        """
        try:
            # COUNT(*) GROUP BY graduation_status WHERE is_active=True
            grad_stmt = (
                select(
                    AgentLearning.graduation_status,
                    func.count().label("count"),
                )
                .where(AgentLearning.is_active == True)  # noqa: E712
                .group_by(AgentLearning.graduation_status)
            )
            grad_result = await self.db.execute(grad_stmt)
            grad_rows = grad_result.all()

            by_status = {r.graduation_status or "active": r.count for r in grad_rows}
            total_active_all = sum(by_status.values())

            # COUNT(*) GROUP BY learning_type WHERE is_active=True
            type_stmt = (
                select(
                    AgentLearning.learning_type,
                    func.count().label("count"),
                    func.sum(AgentLearning.hit_count).label("total_hits"),
                )
                .where(AgentLearning.is_active == True)  # noqa: E712
                .group_by(AgentLearning.learning_type)
            )
            type_result = await self.db.execute(type_stmt)
            type_rows = type_result.all()

            by_type = {
                r.learning_type: r.count
                for r in type_rows
            }
            total_hits = sum((r.total_hits or 0) for r in type_rows)

            return {
                "total": total_active_all,
                "active": by_status.get("active", 0),
                "graduated": by_status.get("graduated", 0),
                "chronic": by_status.get("chronic", 0),
                "by_type": by_type,
                "total_hits": total_hits,
            }

        except Exception as e:
            logger.warning("get_stats failed: %s", e)
            return {
                "total": 0, "active": 0, "graduated": 0, "chronic": 0,
                "by_type": {}, "total_hits": 0,
            }

    # ── Graduation System ──────────────────────────────────

    async def update_graduation(self, learning_id: int, success: bool) -> Optional[str]:
        """
        Update graduation status based on success/failure.

        On success: increment consecutive_success_count, update last_applied_at.
            If consecutive_success_count >= 7 and status == 'active': graduate it.
        On failure: reset consecutive_success_count to 0, increment failure_count.
            If failure_count >= 3 and status == 'active': flag as 'chronic'.

        Returns:
            New graduation_status if changed, None otherwise.
        """
        try:
            stmt = select(AgentLearning).where(AgentLearning.id == learning_id)
            result = await self.db.execute(stmt)
            record = result.scalar_one_or_none()
            if not record:
                return None

            old_status = record.graduation_status or "active"
            new_status = None

            if success:
                record.consecutive_success_count = (record.consecutive_success_count or 0) + 1
                record.last_applied_at = datetime.now(timezone.utc)
                # Graduate after 7 consecutive successes
                if record.consecutive_success_count >= 7 and old_status == "active":
                    record.graduation_status = "graduated"
                    new_status = "graduated"
                    logger.info(
                        "Learning #%d GRADUATED (7+ consecutive successes): %s",
                        learning_id, record.content[:60],
                    )
            else:
                # Rolling window: decrement by 2 instead of full reset (min 0)
                # This allows recovery from occasional failures
                record.consecutive_success_count = max(
                    0, (record.consecutive_success_count or 0) - 2
                )
                record.failure_count = (record.failure_count or 0) + 1
                # Flag as chronic after 3 total failures
                if record.failure_count >= 3 and old_status == "active":
                    record.graduation_status = "chronic"
                    new_status = "chronic"
                    logger.warning(
                        "Learning #%d flagged CHRONIC (3+ failures): %s",
                        learning_id, record.content[:60],
                    )

            await self.db.commit()
            return new_status

        except Exception as e:
            logger.warning("update_graduation failed for #%d: %s", learning_id, e)
            await self.db.rollback()
            return None

    async def get_pending_graduations(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query learnings ready for graduation or chronic flagging.

        Returns:
            {"ready_to_graduate": [...], "ready_for_chronic": [...]}
        """
        try:
            # Active learnings with 7+ consecutive successes -> graduate
            grad_stmt = (
                select(AgentLearning)
                .where(and_(
                    AgentLearning.is_active == True,  # noqa: E712
                    AgentLearning.graduation_status == "active",
                    AgentLearning.consecutive_success_count >= 7,
                ))
            )
            grad_result = await self.db.execute(grad_stmt)
            grad_records = grad_result.scalars().all()

            # Active learnings with 3+ failures -> chronic
            chronic_stmt = (
                select(AgentLearning)
                .where(and_(
                    AgentLearning.is_active == True,  # noqa: E712
                    AgentLearning.graduation_status == "active",
                    AgentLearning.failure_count >= 3,
                ))
            )
            chronic_result = await self.db.execute(chronic_stmt)
            chronic_records = chronic_result.scalars().all()

            return {
                "ready_to_graduate": [
                    {"id": r.id, "content": r.content, "hit_count": r.hit_count,
                     "consecutive_success_count": r.consecutive_success_count}
                    for r in grad_records
                ],
                "ready_for_chronic": [
                    {"id": r.id, "content": r.content, "hit_count": r.hit_count,
                     "failure_count": r.failure_count}
                    for r in chronic_records
                ],
            }

        except Exception as e:
            logger.warning("get_pending_graduations failed: %s", e)
            return {"ready_to_graduate": [], "ready_for_chronic": []}

    async def batch_graduate(self, learning_ids: List[int]) -> int:
        """Batch update learnings to 'graduated' status."""
        if not learning_ids:
            return 0
        try:
            stmt = (
                update(AgentLearning)
                .where(AgentLearning.id.in_(learning_ids))
                .values(graduation_status="graduated")
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount
        except Exception as e:
            logger.warning("batch_graduate failed: %s", e)
            await self.db.rollback()
            return 0

    async def batch_mark_chronic(self, learning_ids: List[int]) -> int:
        """Batch update learnings to 'chronic' status."""
        if not learning_ids:
            return 0
        try:
            stmt = (
                update(AgentLearning)
                .where(AgentLearning.id.in_(learning_ids))
                .values(graduation_status="chronic")
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount
        except Exception as e:
            logger.warning("batch_mark_chronic failed: %s", e)
            await self.db.rollback()
            return 0
