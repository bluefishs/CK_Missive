"""
標案檢索 API 模組 — 拆分自 tender.py (844L → 5 sub-modules)

Sub-modules:
  - search.py        搜尋/詳情/推薦/即時 (6 endpoints)  — 公開（標案為公開資料）
  - graph_case.py    圖譜/建案 (2 endpoints)           — 公開
  - subscriptions.py 訂閱/書籤/廠商關注 (12 endpoints) — ✅ 需認證（個人化資料）
  - analytics.py     分析儀表板 (6 endpoints)          — ✅ 需認證（商業分析）

2026-04-18: 補 subscriptions / analytics auth，修正公網匿名可 CRUD 全公司訂閱的漏洞。
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import require_auth
from .search import router as search_router
from .graph_case import router as graph_case_router
from .subscriptions import router as subscriptions_router
from .analytics import router as analytics_router

router = APIRouter(prefix="/tender", tags=["標案檢索"])
router.include_router(search_router)
router.include_router(graph_case_router)
router.include_router(subscriptions_router, dependencies=[Depends(require_auth())])
router.include_router(analytics_router, dependencies=[Depends(require_auth())])
