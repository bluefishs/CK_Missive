"""
公文行事曆整合 API 端點 (核心模組)
此為系統中唯一且統一的日曆事件 API 來源，並包含完整的 CRUD 功能
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from ...extended.models import User, OfficialDocument, DocumentCalendarEvent
from ...services.document_calendar_service import DocumentCalendarService
from ...services.document_calendar_integrator import DocumentCalendarIntegrator
from app.schemas.document_calendar import SyncStatusResponse, DocumentCalendarEventUpdate
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

calendar_service = DocumentCalendarService()
calendar_integrator = DocumentCalendarIntegrator()

# ... (保留 GET /events, GET /documents/{id}/local-events, POST /documents/{id}/local-events 等現有端點) ...

@router.put("/events/{event_id}", summary="更新日曆事件")
async def update_calendar_event(
    event_id: int,
    event_update: DocumentCalendarEventUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """更新一個已存在的日曆事件。"""
    # 權限檢查：確保只有事件的建立者或負責人可以修改
    event_to_update = await calendar_service.get_event(db, event_id)
    if not event_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")
    
    if event_to_update.created_by != current_user.id and event_to_update.assigned_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您沒有權限修改此事件")

    updated_event = await calendar_service.update_event(db, event_id=event_id, event_update=event_update)
    if not updated_event:
        # 這個情況理論上不會發生，因為上面已經檢查過
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="更新過程中找不到指定的事件")
    
    return updated_event

@router.get("/users/{user_id}/calendar-events", summary="獲取使用者的日曆事件")
async def get_user_calendar_events(
    user_id: int,
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取指定使用者的日曆事件"""
    try:
        # 權限檢查：只能查看自己的事件（除非是管理員）
        if user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己的日曆事件"
            )

        # 設定預設日期範圍
        if not start_date or not end_date:
            now = datetime.now()
            start_dt = now - timedelta(days=30)
            end_dt = now + timedelta(days=60)
        else:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)

        # 查詢使用者相關的日曆事件
        query = (
            select(DocumentCalendarEvent, OfficialDocument.doc_number)
            .join(OfficialDocument, DocumentCalendarEvent.document_id == OfficialDocument.id)
            .where(
                DocumentCalendarEvent.start_date >= start_dt,
                DocumentCalendarEvent.start_date <= end_dt,
                or_(
                    DocumentCalendarEvent.assigned_user_id == user_id,
                    DocumentCalendarEvent.created_by == user_id
                )
            )
        )

        result = await db.execute(query)
        events = result.all()

        calendar_events = []
        for event, doc_number in events:
            calendar_events.append({
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "start_date": event.start_date.isoformat(),
                "end_date": event.end_date.isoformat() if event.end_date else None,
                "all_day": event.all_day,
                "event_type": event.event_type,
                "priority": event.priority,
                "location": event.location,
                "document_id": event.document_id,
                "doc_number": doc_number,
                "assigned_user_id": event.assigned_user_id,
                "created_by": event.created_by,
                "created_at": event.created_at.isoformat(),
                "updated_at": event.updated_at.isoformat()
            })

        return {
            "events": calendar_events,
            "total": len(calendar_events),
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting user calendar events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取使用者日曆事件失敗: {str(e)}"
        )

# ... (保留 GET /status 等輔助端點) ...