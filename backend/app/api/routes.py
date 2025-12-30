"""
API 路由設定 (最終修復版) - 包含調試工具
"""
from fastapi import APIRouter
from app.api.endpoints import (
    documents, document_numbers, auth, projects, agencies, vendors,
    document_calendar, users, user_management, admin, site_management,
    system_monitoring, public, csv_import, reminder_management, files,
    documents_enhanced, secure_site_management, pure_calendar,
    # --- 新增 dashboard 匯入 ---
    dashboard, project_notifications, debug, project_vendors, project_staff
)

api_router = APIRouter()

# --- 核心功能模組 ---
# --- 新增儀表板模組 ---
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["儀表板"])
# --- 統計API模組 (使用dashboard模組) ---
api_router.include_router(dashboard.router, prefix="/statistics", tags=["統計"])
# api_router.include_router(documents.router, prefix="/documents", tags=["公文管理"])  # 暫時註釋
api_router.include_router(documents_enhanced.router, prefix="/documents-enhanced", tags=["公文管理 (增強版)"])
api_router.include_router(projects.router, prefix="/projects", tags=["承攬案件"])
api_router.include_router(project_notifications.router, prefix="/project-notifications", tags=["專案通知"])
api_router.include_router(agencies.router, prefix="/agencies", tags=["機關單位"])
api_router.include_router(vendors.router, prefix="/vendors", tags=["廠商管理"])
api_router.include_router(project_vendors.router, prefix="/project-vendors", tags=["案件廠商關聯"])
api_router.include_router(project_staff.router, prefix="/project-staff", tags=["案件承辦同仁"])

# --- 統一的行事曆模組 ---
api_router.include_router(document_calendar.router, prefix="/calendar", tags=["行事曆"])
api_router.include_router(pure_calendar.router, prefix="/pure-calendar", tags=["純行事曆 (相容)"])

# --- 系統與管理模組 ---
api_router.include_router(auth.router, prefix="/auth", tags=["認證"])
api_router.include_router(users.router, prefix="/users", tags=["使用者"])
api_router.include_router(user_management.router, prefix="/admin/user-management", tags=["權限管理"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理後台"])
api_router.include_router(site_management.router, prefix="/site-management", tags=["網站管理"])
api_router.include_router(secure_site_management.router, prefix="/secure-site-management", tags=["安全網站管理"])
api_router.include_router(system_monitoring.router, prefix="/system", tags=["系統監控"])
api_router.include_router(reminder_management.router, prefix="/reminder-management", tags=["提醒管理"])

# --- 其他輔助模組 ---
api_router.include_router(document_numbers.router, prefix="/document-numbers", tags=["發文字號"])
api_router.include_router(files.router, prefix="/files", tags=["檔案管理"])
api_router.include_router(csv_import.router, prefix="/csv-import", tags=["CSV匯入"])
api_router.include_router(public.router, prefix="/public", tags=["公開API"])
api_router.include_router(debug.router, prefix="/debug", tags=["調試工具"])  # Debug routes