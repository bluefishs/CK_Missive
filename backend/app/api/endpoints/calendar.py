"""
行事曆管理 API 端點
最終修復版：解決了因時區處理不當導致的載入失敗問題
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

# 導入資料庫連線和模型
from app.db.database import get_async_db
from app.extended.models import DocumentCalendarEvent, OfficialDocument, User
from app.api.endpoints.auth import get_current_user
from app.schemas.calendar import CalendarEventCreate, CalendarEventResponse
import logging

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
        logger.error(f"Error getting unified calendar events from /calendar: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取行事曆事件失敗: {str(e)}"
        )

# ... (保留其他模擬端點) ...
@router.get("/status", dependencies=[])
async def get_calendar_status():
    return {"calendar_available": True, "message": "基本行事曆功能可用"}

@router.post("/events")
async def create_calendar_event(event: CalendarEventCreate):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="此功能已停用。請由公文系統建立日曆事件。")