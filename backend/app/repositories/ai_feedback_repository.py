# -*- coding: utf-8 -*-
"""
AI 對話回饋 Repository

v1.0.0 - 2026-02-27
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import AIConversationFeedback
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AIFeedbackRepository(BaseRepository[AIConversationFeedback]):
    """AI 對話回饋資料存取"""

    def __init__(self, db: AsyncSession):
        super().__init__(AIConversationFeedback, db)

    async def submit_feedback(
        self,
        conversation_id: str,
        message_index: int,
        feature_type: str,
        score: int,
        user_id: Optional[int] = None,
        question: Optional[str] = None,
        answer_preview: Optional[str] = None,
        feedback_text: Optional[str] = None,
        latency_ms: Optional[int] = None,
        model: Optional[str] = None,
    ) -> int:
        """
        提交回饋，同一 conversation + message_index 防重複。
        返回記錄 ID。
        """
        # 防重複
        existing = await self.db.execute(
            select(AIConversationFeedback).where(
                AIConversationFeedback.conversation_id == conversation_id,
                AIConversationFeedback.message_index == message_index,
            )
        )
        row = existing.scalars().first()
        if row:
            # 更新已存在的回饋
            row.score = score
            if feedback_text:
                row.feedback_text = feedback_text
            await self.db.flush()
            return row.id

        record = AIConversationFeedback(
            user_id=user_id,
            conversation_id=conversation_id,
            message_index=message_index,
            feature_type=feature_type,
            score=score,
            question=question,
            answer_preview=answer_preview,
            feedback_text=feedback_text,
            latency_ms=latency_ms,
            model=model,
        )
        self.db.add(record)
        await self.db.flush()
        return record.id

    async def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """取得回饋統計"""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.count(AIConversationFeedback.id).label("total"),
                func.sum(case(
                    (AIConversationFeedback.score == 1, 1), else_=0
                )).label("positive"),
                func.sum(case(
                    (AIConversationFeedback.score == -1, 1), else_=0
                )).label("negative"),
            ).where(AIConversationFeedback.created_at >= since)
        )
        row = result.one()
        total = row.total or 0
        positive = row.positive or 0
        negative = row.negative or 0

        # 按 feature_type 分組
        by_feature_result = await self.db.execute(
            select(
                AIConversationFeedback.feature_type,
                func.count(AIConversationFeedback.id).label("total"),
                func.sum(case(
                    (AIConversationFeedback.score == 1, 1), else_=0
                )).label("positive"),
                func.sum(case(
                    (AIConversationFeedback.score == -1, 1), else_=0
                )).label("negative"),
            ).where(
                AIConversationFeedback.created_at >= since
            ).group_by(AIConversationFeedback.feature_type)
        )

        by_feature = {}
        for feat_row in by_feature_result.all():
            feat_total = feat_row.total or 0
            feat_pos = feat_row.positive or 0
            by_feature[feat_row.feature_type] = {
                "total": feat_total,
                "positive": feat_pos,
                "negative": feat_row.negative or 0,
                "positive_rate": round(feat_pos / feat_total, 2) if feat_total > 0 else 0,
            }

        # 最近的負面回饋（方便改進）
        neg_result = await self.db.execute(
            select(AIConversationFeedback).where(
                AIConversationFeedback.score == -1,
                AIConversationFeedback.created_at >= since,
            ).order_by(AIConversationFeedback.created_at.desc()).limit(10)
        )
        recent_negative = []
        for item in neg_result.scalars().all():
            recent_negative.append({
                "id": item.id,
                "conversation_id": item.conversation_id,
                "message_index": item.message_index,
                "feature_type": item.feature_type,
                "score": item.score,
                "question": item.question,
                "answer_preview": item.answer_preview,
                "feedback_text": item.feedback_text,
                "latency_ms": item.latency_ms,
                "model": item.model,
                "user_id": item.user_id,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })

        return {
            "total_feedback": total,
            "positive_count": positive,
            "negative_count": negative,
            "positive_rate": round(positive / total, 2) if total > 0 else 0,
            "by_feature": by_feature,
            "recent_negative": recent_negative,
        }
