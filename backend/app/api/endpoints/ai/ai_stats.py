"""
AI 統計 API 端點

Version: 2.0.0
Created: 2026-02-06
Updated: 2026-02-07 - 改用 AIStatsManager (Redis 持久化)

端點:
- POST /ai/stats - 取得 AI 使用統計
- POST /ai/stats/reset - 重設統計資料
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.dependencies import optional_auth
from app.services.ai.base_ai_service import BaseAIService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stats")
async def get_ai_stats(
    current_user=Depends(optional_auth()),
) -> Dict[str, Any]:
    """
    取得 AI 使用統計

    返回所有 AI 服務的使用統計資料，包含：
    - total_requests: 總請求數
    - by_feature: 按功能分類的統計
    - rate_limit_hits: 速率限制觸發次數
    - groq_requests / ollama_requests / fallback_requests: 各 provider 使用次數
    - start_time: 統計開始時間
    - source: "redis" 或 "memory" (資料來源)
    """
    logger.info("取得 AI 使用統計")
    return await BaseAIService.get_stats()


@router.post("/stats/reset")
async def reset_ai_stats(
    current_user=Depends(optional_auth()),
) -> Dict[str, str]:
    """
    重設 AI 使用統計

    清除所有統計資料並重新開始計數 (Redis + 記憶體)。
    """
    logger.info("重設 AI 統計資料")
    await BaseAIService.reset_stats()
    return {"message": "AI 統計資料已重設"}
