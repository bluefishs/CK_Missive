"""
AI API 端點模組

Version: 1.0.0
Created: 2026-02-04
"""

from fastapi import APIRouter

from .document_ai import router as document_ai_router

router = APIRouter(prefix="/ai", tags=["AI"])

# 註冊子路由
router.include_router(document_ai_router)
