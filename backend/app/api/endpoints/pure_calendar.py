"""
純粹行事曆 API 端點
最終修復版：解決了因時區處理不當導致的載入失敗問題
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

# 導入資料庫連線和模型
from app.db.database import get_async_db
from app.extended.models import DocumentCalendarEvent, OfficialDocument, User
from app.api.endpoints.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/events")
async def get_calendar_events(
    start: Optional[str] = Query(None, description="查詢範圍開始日期 (ISO 格式)"),
    end: Optional[str] = Query(None, description="查詢範圍結束日期 (ISO 格式)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取統一的行事曆事件列表，包含公文日曆事件"""
    try:
        # 如果前端未提供日期範圍，則使用預設值（今天前後30/60天）
        if not start or not end:
            now = datetime.now()
            start_date = now - timedelta(days=30)
            end_date = now + timedelta(days=60)
        else:
            # 關鍵修復：將前端傳來的 UTC 日期字串轉換為帶時區的 datetime 物件
            aware_start = datetime.fromisoformat(start.replace('Z', '+00:00'))
            aware_end = datetime.fromisoformat(end.replace('Z', '+00:00'))
            # 然後移除時區資訊，使其變為 naive datetime，以匹配資料庫中的儲存格式
            start_date = aware_start.replace(tzinfo=None)
            end_date = aware_end.replace(tzinfo=None)

        # 查詢公文日曆事件，條件為：使用者是負責人 或 使用者是建立者
        doc_events_query = (
            select(DocumentCalendarEvent, OfficialDocument.doc_number)
            .join(OfficialDocument, DocumentCalendarEvent.document_id == OfficialDocument.id)
            .where(
                DocumentCalendarEvent.start_date >= start_date,
                DocumentCalendarEvent.start_date <= end_date,
                or_(
                    DocumentCalendarEvent.assigned_user_id == current_user.id,
                    DocumentCalendarEvent.created_by == current_user.id
                )
            )
        )
        doc_events_result = await db.execute(doc_events_query)
        document_events = doc_events_result.all()

        all_events = []
        for event, doc_number in document_events:
            event_color = {
                'deadline': '#f5222d', # 紅色
                'reminder': '#faad14', # 黃色
                'meeting': '#722ed1',  # 紫色
                'review': '#1890ff'   # 藍色
            }.get(event.event_type, '#1890ff')

            all_events.append({
                "id": f"doc_{event.id}",
                "title": event.title,
                "start": event.start_date.isoformat(),
                "end": event.end_date.isoformat() if event.end_date else event.start_date.isoformat(),
                "allDay": event.all_day,
                "color": event_color,
                "extendedProps": {
                    "type": "document_event",
                    "description": event.description,
                    "location": event.location,
                    "priority": event.priority,
                    "document_id": event.document_id,
                    "doc_number": doc_number,
                    "event_type": event.event_type
                }
            })

        return all_events

    except Exception as e:
        logger.error(f"Error getting unified calendar events from /pure-calendar: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取行事曆事件失敗: {str(e)}"
        )

@router.get("/stats")
async def get_calendar_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取行事曆統計資料"""
    try:
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
            "active_documents": 0  # placeholder
        }

    except Exception as e:
        logger.error(f"Error getting calendar stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取統計資料失敗: {str(e)}"
        )

@router.get("/categories")
async def get_calendar_categories(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取行事曆事件分類"""
    try:
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
                    "color": "#1976d2",  # 預設顏色
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
        logger.error(f"Error getting calendar categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取分類失敗: {str(e)}"
        )

# ... (保留其他模擬端點) ...
@router.post("/events")
async def create_calendar_event(event_data: dict):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="此功能已停用。請由公文系統建立日曆事件。")