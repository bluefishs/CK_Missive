"""
公文行事曆整合 API 模組

將原本 985 行的單一檔案拆分為模組化架構。

模組結構：
- common.py - 共用依賴（模型、Schema、工具函數）
- events.py - 事件 CRUD（8 端點）
- sync.py - Google Calendar 同步（3 端點）
- stats.py - 統計與分類（3 端點）
- scheduler.py - 同步排程器控制（5 端點）

API 路徑保持不變：/calendar/*

@version 1.0.0
@date 2026-01-22
"""
from fastapi import APIRouter

# 導入所有子路由
from .events import router as events_router
from .sync import router as sync_router
from .stats import router as stats_router
from .scheduler import router as scheduler_router

# 建立主路由（注意：不設置 prefix，由 routes.py 統一設置）
router = APIRouter()

# 按功能聚合所有子路由
# 1. 事件 CRUD 操作
router.include_router(events_router)

# 2. Google Calendar 同步
router.include_router(sync_router)

# 3. 統計與分類
router.include_router(stats_router)

# 4. 同步排程器控制
router.include_router(scheduler_router)

__all__ = ["router"]
