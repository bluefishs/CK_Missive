"""
承攬案件管理 API 端點模組

將原 projects.py 拆分為以下子模組：
- crud: CRUD 操作（列表、詳情、建立、更新、刪除）
- stats: 統計與下拉選單（年度、類別、狀態、統計資料）

@version 4.0.0
@date 2026-02-11
"""
from fastapi import APIRouter

from .crud import router as crud_router
from .stats import router as stats_router

# 統一路由器
router = APIRouter()

# 註冊所有子路由
router.include_router(crud_router, tags=["承攬案件CRUD"])
router.include_router(stats_router, tags=["承攬案件統計"])

__all__ = ["router"]
