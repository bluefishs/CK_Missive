"""
AI API 端點模組

Version: 1.3.0
Created: 2026-02-04
Updated: 2026-02-08 - 新增 AI Prompt 版本管理端點
"""

from fastapi import APIRouter

from .document_ai import router as document_ai_router
from .ai_stats import router as ai_stats_router
from .synonyms import router as synonyms_router
from .prompts import router as prompts_router
from .search_history import router as search_history_router

router = APIRouter(prefix="/ai", tags=["AI"])

# 註冊子路由
router.include_router(document_ai_router)
router.include_router(ai_stats_router)
router.include_router(synonyms_router)
router.include_router(prompts_router)
router.include_router(search_history_router)
