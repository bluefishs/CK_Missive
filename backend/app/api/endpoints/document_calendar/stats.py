"""
公文行事曆模組 - 統計與分類 API

包含端點：
- /stats - 獲取行事曆統計資料
- /categories - 獲取行事曆事件分類
- /status - 獲取行事曆服務狀態

@version 1.0.0
@date 2026-01-22
"""
from fastapi import APIRouter

from .common import (
    Depends, HTTPException, status,
    AsyncSession, select, or_, func,
    get_async_db, get_current_user,
    User, DocumentCalendarEvent,
    logger, datetime, timedelta
)

router = APIRouter()


@router.post("/stats", summary="獲取行事曆統計資料")
async def get_calendar_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取行事曆統計資料"""
    try:
        now = datetime.now()

        # 使用者權限過濾
        user_filter = or_(
            DocumentCalendarEvent.assigned_user_id == current_user.id,
            DocumentCalendarEvent.created_by == current_user.id
        )

        # 總事件數
        total_query = select(func.count(DocumentCalendarEvent.id)).where(user_filter)
        total_events = (await db.execute(total_query)).scalar() or 0

        # 今日事件
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        today_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date >= today_start,
            DocumentCalendarEvent.start_date < today_end,
            user_filter
        )
        today_events = (await db.execute(today_query)).scalar() or 0

        # 本週事件
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        week_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date >= week_start,
            DocumentCalendarEvent.start_date < week_end,
            user_filter
        )
        week_events = (await db.execute(week_query)).scalar() or 0

        # 本月事件
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        month_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date >= month_start,
            DocumentCalendarEvent.start_date < next_month,
            user_filter
        )
        month_events = (await db.execute(month_query)).scalar() or 0

        # 即將到來事件
        upcoming_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date > now,
            user_filter
        )
        upcoming_events = (await db.execute(upcoming_query)).scalar() or 0

        return {
            "total_events": total_events,
            "today_events": today_events,
            "this_week_events": week_events,
            "this_month_events": month_events,
            "upcoming_events": upcoming_events
        }

    except Exception as e:
        logger.error(f"Error getting calendar stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取統計資料失敗: {str(e)}"
        )


@router.post("/categories", summary="獲取行事曆事件分類")
async def get_calendar_categories(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取行事曆事件分類"""
    try:
        # 預設分類定義
        default_categories = [
            {"value": "reminder", "label": "提醒", "color": "#faad14"},
            {"value": "deadline", "label": "截止日期", "color": "#f5222d"},
            {"value": "meeting", "label": "會議", "color": "#722ed1"},
            {"value": "review", "label": "審查", "color": "#1890ff"},
        ]

        # 查詢資料庫中實際使用的事件類型
        event_types_query = select(DocumentCalendarEvent.event_type).distinct()
        event_types_result = await db.execute(event_types_query)
        db_event_types = event_types_result.scalars().all()

        # 合併預設分類和資料庫中的類型
        existing_values = {cat["value"] for cat in default_categories}
        for event_type in db_event_types:
            if event_type and event_type not in existing_values:
                default_categories.append({
                    "value": event_type,
                    "label": event_type,
                    "color": "#1890ff"
                })

        return {"categories": default_categories}

    except Exception as e:
        logger.error(f"Error getting calendar categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取分類失敗: {str(e)}"
        )


@router.post("/status", summary="獲取行事曆服務狀態")
async def get_calendar_status():
    """獲取行事曆服務狀態"""
    return {
        "calendar_available": True,
        "message": "行事曆服務運作正常",
        "service_type": "integrated",
        "features": ["本地行事曆", "事件提醒", "公文關聯"]
    }
