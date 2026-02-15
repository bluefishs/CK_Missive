"""
事件提醒 CRUD 端點

提供事件提醒的查詢、新增、刪除功能。
拆分自 reminder_management.py

@version 1.0.0
@date 2026-02-11
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.extended.models import (
    User,
    EventReminder,
    DocumentCalendarEvent,
)
from app.schemas.reminder import (
    ReminderActionRequest,
    ReminderStatusResponse,
)
from app.services.document_calendar_integrator import DocumentCalendarIntegrator

router = APIRouter()

# DocumentCalendarIntegrator 仍用 Singleton
calendar_integrator = DocumentCalendarIntegrator()


@router.post("/events/{event_id}/reminders", response_model=ReminderStatusResponse)
async def get_event_reminders_status(
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """獲取特定事件的提醒狀態"""
    try:
        result = await db.execute(
            select(EventReminder).where(EventReminder.event_id == event_id)
        )
        reminders = result.scalars().all()

        by_status: Dict[str, int] = {}
        reminder_list = []
        for r in reminders:
            status = r.status or "pending"
            by_status[status] = by_status.get(status, 0) + 1
            reminder_list.append(
                {
                    "id": r.id,
                    "event_id": r.event_id,
                    "reminder_minutes": getattr(r, "reminder_minutes", 60),
                    "reminder_time": r.reminder_time.isoformat()
                    if r.reminder_time
                    else None,
                    "reminder_type": r.notification_type
                    or r.reminder_type
                    or "system",
                    "notification_type": r.notification_type,
                    "title": getattr(r, "title", None),
                    "status": r.status or "pending",
                    "is_sent": getattr(r, "is_sent", False),
                    "retry_count": getattr(r, "retry_count", 0),
                    "priority": getattr(r, "priority", 3),
                    "message": getattr(r, "message", None),
                }
            )

        return {
            "success": True,
            "total": len(reminders),
            "by_status": by_status,
            "reminders": reminder_list,
        }
    except Exception as e:
        logger.error("獲取提醒狀態失敗: %s", e)
        raise HTTPException(status_code=500, detail="獲取提醒狀態失敗")


@router.post("/documents/{document_id}/reminders", response_model=Dict[str, Any])
async def get_document_reminders_status(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """獲取公文所有事件的提醒狀態"""
    try:
        status = await calendar_integrator.get_reminder_status(
            db=db, document_id=document_id
        )

        if "error" in status:
            raise HTTPException(status_code=400, detail=status["error"])

        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取公文提醒狀態失敗: %s", e)
        raise HTTPException(
            status_code=500, detail="獲取公文提醒狀態失敗"
        )


@router.post("/events/{event_id}/reminders/update-template")
async def update_event_reminder_template(
    event_id: int,
    request: ReminderActionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """新增或刪除事件的提醒"""
    try:
        # 獲取事件
        event_result = await db.execute(
            select(DocumentCalendarEvent).where(
                DocumentCalendarEvent.id == event_id
            )
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="找不到指定的事件")

        if request.action == "add":
            reminder_time = None
            if request.reminder_time:
                reminder_time = datetime.fromisoformat(
                    request.reminder_time.replace("Z", "+00:00")
                )
            elif event.start_date and request.reminder_minutes:
                reminder_time = event.start_date - timedelta(
                    minutes=request.reminder_minutes
                )

            new_reminder = EventReminder(
                event_id=event_id,
                reminder_minutes=request.reminder_minutes or 60,
                reminder_time=reminder_time,
                notification_type=request.reminder_type or "system",
                title=f"事件提醒: {event.title}",
                message=f"您有一個即將到來的事件: {event.title}",
                recipient_user_id=current_user.id,
                status="pending",
                priority=3,
            )
            db.add(new_reminder)
            await db.commit()
            await db.refresh(new_reminder)

            return {
                "success": True,
                "message": "提醒已新增",
                "reminder_id": new_reminder.id,
            }

        elif request.action == "delete":
            if not request.reminder_id:
                raise HTTPException(
                    status_code=400, detail="刪除操作需要提供 reminder_id"
                )

            reminder_result = await db.execute(
                select(EventReminder).where(
                    EventReminder.id == request.reminder_id,
                    EventReminder.event_id == event_id,
                )
            )
            reminder = reminder_result.scalar_one_or_none()
            if not reminder:
                raise HTTPException(status_code=404, detail="找不到指定的提醒")

            await db.delete(reminder)
            await db.commit()

            return {"success": True, "message": "提醒已刪除"}

        else:
            raise HTTPException(
                status_code=400, detail=f"不支援的操作: {request.action}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("提醒操作失敗: %s", e)
        raise HTTPException(status_code=500, detail="操作失敗")
