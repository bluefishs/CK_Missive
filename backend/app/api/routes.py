"""
API 路由設定 (最終修復版) - 包含調試工具

@version 3.0.0
@date 2026-01-18
"""
from fastapi import APIRouter
from app.api.endpoints import (
    document_numbers, document_numbers_crud, auth, agencies, vendors,
    document_calendar, users, user_management, user_permissions, role_permissions,
    admin, site_management,
    system_monitoring, public, csv_import, reminders, files,
    secure_site_management,
    dashboard, project_notifications, debug, project_vendors, project_staff,
    project_agency_contacts, system_notifications, backup, certifications,
    taoyuan_dispatch, deployment, health, knowledge_base, line_webhook
)
# AI 服務模組 (v1.37.0)
from app.api.endpoints.ai import router as ai_router
# 模組化公文管理 API (v3.0.0 重構)
from app.api.endpoints.documents import router as documents_router
# 模組化承攬案件管理 API (v4.0.0 重構)
from app.api.endpoints.projects import router as projects_router

api_router = APIRouter()

# --- 核心功能模組 ---
# --- 新增儀表板模組 ---
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["儀表板"])
# --- 統計API模組 (使用dashboard模組) ---
api_router.include_router(dashboard.router, prefix="/statistics", tags=["統計"])
api_router.include_router(documents_router, prefix="/documents-enhanced", tags=["公文管理"])
api_router.include_router(projects_router, prefix="/projects", tags=["承攬案件"])
api_router.include_router(project_notifications.router, prefix="/project-notifications", tags=["專案通知"])
api_router.include_router(system_notifications.router, prefix="/system-notifications", tags=["系統通知"])
api_router.include_router(agencies.router, prefix="/agencies", tags=["機關單位"])
api_router.include_router(vendors.router, prefix="/vendors", tags=["廠商管理"])
api_router.include_router(project_vendors.router, prefix="/project-vendors", tags=["案件廠商關聯"])
api_router.include_router(project_staff.router, prefix="/project-staff", tags=["案件承辦同仁"])
api_router.include_router(project_agency_contacts.router, prefix="/project-agency-contacts", tags=["專案機關承辦"])

# --- 統一的行事曆模組 (已整合至 /calendar) ---
api_router.include_router(document_calendar.router, prefix="/calendar", tags=["行事曆"])

# --- 系統與管理模組 ---
api_router.include_router(auth.router, prefix="/auth", tags=["認證"])
api_router.include_router(users.router, prefix="/users", tags=["使用者"])
api_router.include_router(certifications.router, prefix="/certifications", tags=["證照管理"])
api_router.include_router(user_management.router, prefix="/admin/user-management", tags=["使用者管理"])
api_router.include_router(user_permissions.router, prefix="/admin/user-management", tags=["權限管理"])
api_router.include_router(role_permissions.router, prefix="/admin/user-management", tags=["角色權限"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理後台"])
api_router.include_router(site_management.router, prefix="/site-management", tags=["網站管理"])
api_router.include_router(secure_site_management.router, prefix="/secure-site-management", tags=["安全網站管理"])
api_router.include_router(system_monitoring.router, prefix="/system", tags=["系統監控"])
api_router.include_router(reminders.router, prefix="/reminder-management", tags=["提醒管理"])

# --- 其他輔助模組 ---
api_router.include_router(document_numbers.router, prefix="/document-numbers", tags=["發文字號"])
api_router.include_router(document_numbers_crud.router, prefix="/document-numbers", tags=["發文字號"])
api_router.include_router(files.router, prefix="/files", tags=["檔案管理"])
api_router.include_router(csv_import.router, prefix="/csv-import", tags=["CSV匯入"])
api_router.include_router(public.router, prefix="/public", tags=["公開API"])
api_router.include_router(debug.router, prefix="/debug", tags=["調試工具"])  # Debug routes
api_router.include_router(backup.router, prefix="/backup", tags=["資料庫備份"])
api_router.include_router(deployment.router, tags=["部署管理"])

# --- 桃園查估派工管理系統 ---
api_router.include_router(taoyuan_dispatch.router, tags=["桃園派工管理"])

# --- 健康監控模組 ---
api_router.include_router(health.router, tags=["健康監控"])

# --- AI 服務模組 (v1.37.0) ---
api_router.include_router(ai_router, tags=["AI服務"])

# --- 知識庫瀏覽模組 ---
api_router.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["知識庫"])

# --- LINE Bot 整合 (v1.83.0) ---
api_router.include_router(line_webhook.router, prefix="/line", tags=["LINE Bot"])

# --- Discord Bot 整合 (v5.2.2) ---
from app.api.endpoints import discord_webhook
api_router.include_router(discord_webhook.router, prefix="/discord", tags=["Discord Bot"])

# --- 數位分身 (v5.2.3) --- 已在 ai/__init__.py 中透過 ai_router 掛載

# --- 專案管理模組 (PM, v1.85.0) ---
from app.api.endpoints.pm import router as pm_router
api_router.include_router(pm_router, prefix="/pm", tags=["專案管理"])

# --- 財務管理模組 (ERP, v1.85.0) ---
from app.api.endpoints.erp import router as erp_router
api_router.include_router(erp_router, prefix="/erp", tags=["財務管理"])

# --- 標案檢索 (v5.3.22) ---
from app.api.endpoints.tender import router as tender_router
api_router.include_router(tender_router)

# --- 資安管理中心 (v5.2.5) ---
from app.api.endpoints.security import router as security_router
api_router.include_router(security_router)
