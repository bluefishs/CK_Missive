"""
安全網站管理模組

將原始 secure_site_management.py (637 行) 模組化為：
- common.py     - CSRF 管理、遞迴查詢、重排序工具
- navigation.py - 導覽列操作端點
- config.py     - 配置管理端點
- security.py   - CSRF token 端點

@version 2.0.0
@date 2026-01-28
"""

from fastapi import APIRouter

from .navigation import router as navigation_router
from .config import router as config_router
from .security import router as security_router

router = APIRouter()
router.include_router(security_router)
router.include_router(navigation_router)
router.include_router(config_router)
