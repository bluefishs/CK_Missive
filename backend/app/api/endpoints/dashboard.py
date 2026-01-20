"""
儀表板專用 API 端點

提供儀表板統計數據和系統概覽資訊。
所有端點需要認證。

@version 2.0.0
@date 2026-01-20
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_async_db
from app.core.dependencies import require_auth, require_admin
from app.extended.models import OfficialDocument as Document, User
from app.schemas.dashboard import (
    DashboardStatsResponse,
    DashboardStats,
    StatisticsOverviewResponse,
    DocumentTypeCount,
    CalendarCategoriesResponse,
    CalendarCategoryItem,
)

router = APIRouter()

@router.post("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    提供儀表板所需的所有統計數據和近期公文列表。
    需要認證。
    """
    try:
        # 1. 高效計算各種狀態的公文數量
        status_query = (
            select(Document.status, func.count(Document.id))
            .group_by(Document.status)
        )
        status_result = await db.execute(status_query)
        status_counts = {status: count for status, count in status_result.all()}

        # 2. 獲取最近的 10 筆公文
        recent_docs_query = (
            select(Document)
            .order_by(Document.created_at.desc())
            .limit(10)
        )
        recent_docs_result = await db.execute(recent_docs_query)
        recent_documents = recent_docs_result.scalars().all()

        # 3. 組合回應數據（使用統一 Schema）
        stats = DashboardStats(
            total=sum(status_counts.values()),
            approved=status_counts.get('使用者確認', 0),
            pending=status_counts.get('收文完成', 0),
            rejected=status_counts.get('收文異常', 0)
        )

        return DashboardStatsResponse(
            stats=stats,
            recent_documents=recent_documents
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法獲取儀表板數據: {str(e)}")

@router.post("/statistics/overview", response_model=StatisticsOverviewResponse)
async def get_statistics_overview(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    提供系統統計概覽。需要認證。
    """
    try:
        # 公文統計
        total_documents_result = await db.execute(select(func.count(Document.id)))
        total_documents = total_documents_result.scalar() or 0

        # 按類型分組的公文數量
        type_query = (
            select(Document.type, func.count(Document.id))
            .group_by(Document.type)
        )
        type_result = await db.execute(type_query)
        document_types = [
            DocumentTypeCount(type=row[0] or "未分類", count=row[1])
            for row in type_result.all()
        ]

        # 使用者統計
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0

        active_users_result = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_users_result.scalar() or 0

        return StatisticsOverviewResponse(
            total_documents=total_documents,
            document_types=document_types,
            total_users=total_users,
            active_users=active_users
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法獲取統計概覽: {str(e)}")

@router.post("/dev-mapping", summary="獲取 API 對應關係 (調試用)")
async def get_api_mapping(
    request: Request,
    current_user: User = Depends(require_admin())
):
    """
    臨時放在儀表板路由中的 API 對應關係調試端點。
    需要管理員權限。
    """
    app = request.app

    all_api_items = []

    # 遍歷所有路由
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods") and hasattr(route, "endpoint"):
            path = route.path
            methods = list(route.methods) if route.methods else []
            endpoint_func = route.endpoint

            # 嘗試從路由處理函數推斷相關模組和服務
            module_name = endpoint_func.__module__
            func_name = endpoint_func.__name__

            # 排除內部或非 API 路由
            if (path.startswith("/openapi.json") or
                path.startswith("/docs") or
                path.startswith("/redoc") or
                path.startswith("/static") or
                path.startswith("/health") or
                path.startswith("/favicon.ico") or
                path == "/"):
                continue

            all_api_items.append({
                "api": f"{' '.join(methods)} {path}",
                "module": module_name,
                "function": func_name,
                "description": f"由 {module_name}.{func_name} 處理"
            })

    # 按 API 路徑排序
    all_api_items.sort(key=lambda x: x["api"])

    return {
        "total_routes": len(all_api_items),
        "routes": all_api_items[:50]  # 限制返回前50個路由以避免過大
    }

# 臨時備用端點：為純行事曆提供必要的API
@router.post("/pure-calendar-stats", summary="純行事曆統計 (臨時)")
async def get_pure_calendar_stats_temp(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """臨時備用：純行事曆統計資料。需要認證。"""
    try:
        from app.extended.models import DocumentCalendarEvent
        from datetime import datetime, timedelta

        # 查詢總事件數
        total_events_query = select(func.count(DocumentCalendarEvent.id))
        total_events = (await db.execute(total_events_query)).scalar() or 0

        # 查詢本月事件數
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = month_start.replace(month=month_start.month + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)

        month_events_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date >= month_start,
            DocumentCalendarEvent.start_date < next_month
        )
        month_events = (await db.execute(month_events_query)).scalar() or 0

        # 查詢今日事件數
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        today_events_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date >= today_start,
            DocumentCalendarEvent.start_date < today_end
        )
        today_events = (await db.execute(today_events_query)).scalar() or 0

        return {
            "total_events": total_events,
            "month_events": month_events,
            "today_events": today_events,
            "active_documents": 0
        }
    except Exception as e:
        return {
            "total_events": 0,
            "month_events": 0,
            "today_events": 0,
            "active_documents": 0
        }

@router.post("/pure-calendar-categories", summary="純行事曆分類 (臨時)")
async def get_pure_calendar_categories_temp(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """臨時備用：純行事曆事件分類。需要認證。"""
    try:
        from app.extended.models import DocumentCalendarEvent

        # 查詢所有事件類型
        event_types_query = select(DocumentCalendarEvent.event_type).distinct()
        event_types_result = await db.execute(event_types_query)
        event_types = event_types_result.scalars().all()

        categories = []
        for event_type in event_types:
            if event_type:
                categories.append({
                    "id": event_type,
                    "name": event_type,
                    "color": "#1976d2",
                    "description": f"{event_type}類型事件"
                })

        # 如果沒有任何分類，提供預設分類
        if not categories:
            categories = [
                {"id": "meeting", "name": "會議", "color": "#1976d2", "description": "會議相關事件"},
                {"id": "deadline", "name": "截止日期", "color": "#f44336", "description": "截止日期相關事件"},
                {"id": "reminder", "name": "提醒", "color": "#ff9800", "description": "提醒事項"}
            ]

        return {"categories": categories}
    except Exception as e:
        return {
            "categories": [
                {"id": "meeting", "name": "會議", "color": "#1976d2", "description": "會議相關事件"},
                {"id": "deadline", "name": "截止日期", "color": "#f44336", "description": "截止日期相關事件"},
                {"id": "reminder", "name": "提醒", "color": "#ff9800", "description": "提醒事項"}
            ]
        }

# 臨時備用端點：為使用者管理提供必要的API
@router.post("/user-management-users", summary="使用者列表 (臨時)")
async def get_users_temp(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """臨時備用：使用者列表。需要管理員權限。"""
    try:
        from app.extended.models import User

        # 查詢使用者
        query = select(User).where(User.is_active == True)
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        result = await db.execute(query)
        users = result.scalars().all()

        # 總數查詢
        total_query = select(func.count(User.id)).where(User.is_active == True)
        total = (await db.execute(total_query)).scalar() or 0

        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            })

        return {
            "users": user_list,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    except Exception as e:
        return {
            "users": [],
            "total": 0,
            "page": page,
            "per_page": per_page
        }

@router.post("/user-management-permissions", summary="可用權限列表 (臨時)")
async def get_available_permissions_temp(
    current_user: User = Depends(require_admin())
):
    """臨時備用：可用權限列表。需要管理員權限。"""
    return {
        "permissions": [
            "documents:read", "documents:create", "documents:edit", "documents:delete",
            "projects:read", "projects:create", "projects:edit", "projects:delete",
            "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
            "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
            "admin:users", "admin:settings", "admin:database", "admin:site_management",
            "reports:view", "reports:export", "calendar:read", "calendar:edit"
        ],
        "roles": [
            {"name": "user", "display_name": "一般使用者", "default_permissions": ["documents:read", "projects:read"]},
            {"name": "admin", "display_name": "管理員", "default_permissions": ["*"]},
            {"name": "superuser", "display_name": "超級管理員", "default_permissions": ["*"]}
        ]
    }
