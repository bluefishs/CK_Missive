"""
公文管理 API 端點模組

將原 documents_enhanced.py 拆分為以下子模組：
- list: 列表、搜尋、篩選
- crud: CRUD 操作
- stats: 統計與下拉選單
- export: 匯出功能
- import_: 匯入功能（使用 import_ 避免與 Python 關鍵字衝突）
- audit: 審計日誌

@version 3.0.0
@date 2026-01-18
"""
from fastapi import APIRouter

from .list import router as list_router
from .crud import router as crud_router
from .stats import router as stats_router
from .export import router as export_router
from .import_ import router as import_router
from .audit import router as audit_router

# 統一路由器
router = APIRouter()

# 註冊所有子路由
router.include_router(list_router, tags=["公文列表"])
router.include_router(crud_router, tags=["公文CRUD"])
router.include_router(stats_router, tags=["公文統計"])
router.include_router(export_router, tags=["公文匯出"])
router.include_router(import_router, tags=["公文匯入"])
router.include_router(audit_router, tags=["公文審計"])

__all__ = ["router"]
