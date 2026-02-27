# -*- coding: utf-8 -*-
"""
AI 對話回饋 + 使用分析 API 端點

v1.0.0 - 2026-02-27
"""
import logging
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.core.dependencies import require_auth, require_admin
from app.extended.models import User
from app.repositories.ai_feedback_repository import AIFeedbackRepository
from app.schemas.ai_feedback import (
    AIFeedbackSubmitRequest,
    AIFeedbackSubmitResponse,
    AIFeedbackStatsResponse,
    AIAnalyticsOverviewResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/feedback",
    response_model=AIFeedbackSubmitResponse,
    summary="提交 AI 回答回饋",
)
async def submit_feedback(
    request: AIFeedbackSubmitRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """
    提交 Agent / RAG 回答的使用者回饋（thumbs up/down）。
    同一對話 + 訊息序號不會重複建立，而是更新。
    """
    try:
        repo = AIFeedbackRepository(db)
        record_id = await repo.submit_feedback(
            conversation_id=request.conversation_id,
            message_index=request.message_index,
            feature_type=request.feature_type,
            score=request.score,
            user_id=current_user.id,
            question=request.question,
            answer_preview=request.answer_preview,
            feedback_text=request.feedback_text,
            latency_ms=request.latency_ms,
            model=request.model,
        )
        await db.commit()
        logger.info(
            f"[FEEDBACK] user={current_user.id} conv={request.conversation_id} "
            f"msg={request.message_index} score={request.score} type={request.feature_type}"
        )
        return AIFeedbackSubmitResponse(
            success=True,
            message=f"回饋已記錄 (ID: {record_id})",
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"提交回饋失敗: {e}", exc_info=True)
        return AIFeedbackSubmitResponse(success=False, message=str(e))


@router.post(
    "/feedback/stats",
    response_model=AIFeedbackStatsResponse,
    summary="取得 AI 回饋統計",
)
async def get_feedback_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
):
    """取得 AI 回答回饋統計（管理員）"""
    try:
        repo = AIFeedbackRepository(db)
        stats = await repo.get_feedback_stats(days=30)
        return AIFeedbackStatsResponse(success=True, **stats)
    except Exception as e:
        logger.error(f"取得回饋統計失敗: {e}", exc_info=True)
        return AIFeedbackStatsResponse(success=False)


@router.post(
    "/analytics/overview",
    response_model=AIAnalyticsOverviewResponse,
    summary="系統使用分析總覽",
)
async def get_analytics_overview(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin()),
):
    """
    彙整 AI 功能使用量 + 回饋統計 + 搜尋統計，
    供管理者了解哪些功能有人用、哪些沒人用。
    """
    try:
        # 1. AI 功能使用量 (from AIStatsManager)
        ai_feature_usage = {}
        try:
            from app.services.ai.base_ai_service import BaseAIService
            stats = await BaseAIService.get_stats()
            ai_feature_usage = stats.get("by_feature", {})
        except Exception as e:
            logger.warning(f"讀取 AI 統計失敗: {e}")

        # 2. 回饋統計
        feedback_summary = {}
        try:
            repo = AIFeedbackRepository(db)
            feedback_summary = await repo.get_feedback_stats(days=30)
        except Exception as e:
            logger.warning(f"讀取回饋統計失敗: {e}")

        # 3. 搜尋統計
        search_stats = {}
        try:
            from app.repositories.ai_search_history_repository import AISearchHistoryRepository
            search_repo = AISearchHistoryRepository(db)
            search_stats = await search_repo.get_stats()
        except Exception as e:
            logger.warning(f"讀取搜尋統計失敗: {e}")

        # 4. 零使用功能
        all_features = {
            "summary", "classify", "keywords", "natural_search",
            "parse_intent", "agency_match", "rag_query",
            "agent_query", "entity_extract", "graph_query",
            "embedding", "relation_graph",
        }
        used_features = set(ai_feature_usage.keys()) if ai_feature_usage else set()
        unused_features = sorted(all_features - used_features)

        return AIAnalyticsOverviewResponse(
            success=True,
            ai_feature_usage=ai_feature_usage,
            feedback_summary=feedback_summary,
            search_stats=search_stats,
            unused_features=unused_features,
        )
    except Exception as e:
        logger.error(f"取得使用分析失敗: {e}", exc_info=True)
        return AIAnalyticsOverviewResponse(success=False)
