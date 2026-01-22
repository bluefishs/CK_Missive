"""
桃園派工管理系統 API 模組

將原本 2800+ 行的單一檔案拆分為模組化架構。

模組結構：
- common.py - 共用依賴（模型、Schema、工具函數）
- projects.py - 轄管工程 CRUD + 匯入
- dispatch.py - 派工紀錄 CRUD + 匯入
- project_dispatch_links.py - 工程-派工關聯
- dispatch_document_links.py - 派工-公文關聯
- document_project_links.py - 公文-工程關聯
- payments.py - 契金管控
- master_control.py - 總控表 + 輔助端點
- statistics.py - 統計資料
- attachments.py - 附件管理

API 路徑保持不變：/taoyuan-dispatch/*

@version 2.0.0
@date 2026-01-22
"""
from fastapi import APIRouter

# 導入所有子路由
from .projects import router as projects_router
from .dispatch import router as dispatch_router
from .project_dispatch_links import router as project_dispatch_links_router
from .dispatch_document_links import router as dispatch_document_links_router
from .document_project_links import router as document_project_links_router
from .payments import router as payments_router
from .master_control import router as master_control_router
from .statistics import router as statistics_router
from .attachments import router as attachments_router

# 建立主路由
router = APIRouter(prefix="/taoyuan-dispatch", tags=["桃園派工管理"])

# 按優先順序聚合所有子路由
# 1. 基礎資料操作
router.include_router(projects_router)
router.include_router(dispatch_router)

# 2. 關聯操作
router.include_router(project_dispatch_links_router)
router.include_router(dispatch_document_links_router)
router.include_router(document_project_links_router)

# 3. 契金與總控
router.include_router(payments_router)
router.include_router(master_control_router)

# 4. 統計與附件
router.include_router(statistics_router)
router.include_router(attachments_router)

__all__ = ["router"]
