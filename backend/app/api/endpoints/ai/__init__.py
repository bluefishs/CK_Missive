"""
AI API 端點模組

Version: 1.1.0
Created: 2026-02-04
Updated: 2026-02-06 - 新增 AI 統計端點
"""

from fastapi import APIRouter

from .document_ai import router as document_ai_router
from .ai_stats import router as ai_stats_router

router = APIRouter(prefix="/ai", tags=["AI"])

# 註冊子路由
router.include_router(document_ai_router)
router.include_router(ai_stats_router)
