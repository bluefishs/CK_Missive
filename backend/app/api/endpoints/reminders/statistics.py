"""
提醒統計與批量處理端點

@version 1.0.0
@date 2026-02-11
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
from sqlalchemy import func, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.extended.models import User, EventReminder
from app.schemas.reminder import BatchProcessResponse
from app.api.endpoints.reminders.events import calendar_integrator
from app.services.reminder_service import ReminderService

router = APIRouter()


@router.post("/process-pending", response_model=BatchProcessResponse)
async def process_pending_reminders(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """批量處理待發送的提醒"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="權限不足")

        stats = await calendar_integrator.process_pending_reminders(db)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error("處理提醒失敗: %s", e)
        raise HTTPException(status_code=500, detail="處理提醒失敗")


@router.post("/pending-count")
async def get_pending_reminders_count(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """獲取待處理提醒數量"""
    try:
        reminder_service = ReminderService(db)
        pending_reminders = await reminder_service.get_pending_reminders()
        return {
            "count": len(pending_reminders),
            "reminders": [
                {
                    "id": reminder.id,
                    "event_id": reminder.event_id,
                    "reminder_time": reminder.reminder_time.isoformat(),
                    "notification_type": reminder.notification_type,
                    "priority": reminder.priority,
                    "retry_count": reminder.retry_count,
                }
                for reminder in pending_reminders[:20]
            ],
        }
    except Exception as e:
        logger.error("獲取待處理提醒失敗: %s", e)
        raise HTTPException(
            status_code=500, detail="獲取待處理提醒失敗"
        )


@router.post("/statistics")
async def get_reminder_statistics(
    days: int = Query(30, description="統計天數"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """獲取提醒統計資訊"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        result = await db.execute(
            select(
                EventReminder.status,
                EventReminder.notification_type,
                func.count(EventReminder.id).label("count"),
            )
            .where(
                and_(
                    EventReminder.created_at >= start_date,
                    EventReminder.created_at <= end_date,
                )
            )
            .group_by(EventReminder.status, EventReminder.notification_type)
        )

        statistics = {}
        for status, notification_type, count in result:
            if status not in statistics:
                statistics[status] = {}
            statistics[status][notification_type] = count

        return {
            "period": f"{days} 天",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "statistics": statistics,
        }
    except Exception as e:
        logger.error("獲取統計資訊失敗: %s", e)
        raise HTTPException(
            status_code=500, detail="獲取統計資訊失敗"
        )
