"""
提醒管理 API 模組

拆分自 reminder_management.py，分為 4 個子模組：
- events: 事件提醒 CRUD
- statistics: 統計、批量處理、待處理查詢
- templates: 預設模板、測試提醒
- scheduler: 排程器控制

@version 1.0.0
@date 2026-02-11
"""
from fastapi import APIRouter

from .events import router as events_router
from .statistics import router as statistics_router
from .templates import router as templates_router
from .scheduler import router as scheduler_router

router = APIRouter()

router.include_router(events_router)
router.include_router(statistics_router)
router.include_router(templates_router)
router.include_router(scheduler_router)
