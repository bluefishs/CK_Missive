"""
提醒模板與測試端點

@version 1.0.0
@date 2026-02-11
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.extended.models import User, EventReminder
from app.services.reminder_service import ReminderService

router = APIRouter()


@router.post("/templates/defaults")
async def get_default_reminder_templates(
    current_user: User = Depends(get_current_user),
):
    """獲取預設提醒模板"""
    return {
        "templates": ReminderService.DEFAULT_REMINDER_TEMPLATES,
        "description": "預設提醒模板配置，可作為自訂模板的參考",
    }


@router.post("/send-test-reminder")
async def send_test_reminder(
    recipient_email: Optional[str] = Query(
        None, description="測試收件人信箱（email類型時必填）"
    ),
    recipient_user_id: Optional[int] = Query(
        None, description="測試收件人ID（system類型時必填）"
    ),
    notification_type: str = Query("email", description="通知類型（email/system）"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """發送測試提醒（僅管理員）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="權限不足")

        if notification_type not in ["email", "system"]:
            raise HTTPException(
                status_code=400,
                detail="不支援的通知類型，僅支援 email 和 system",
            )

        if notification_type == "email" and not recipient_email:
            raise HTTPException(
                status_code=400, detail="email類型提醒需要提供收件人信箱"
            )

        if notification_type == "system" and not recipient_user_id:
            raise HTTPException(
                status_code=400, detail="system類型提醒需要提供收件人用戶ID"
            )

        test_reminder = EventReminder(
            event_id=0,
            reminder_minutes=0,
            reminder_time=datetime.now(),
            notification_type=notification_type,
            title="系統測試提醒",
            message="這是一則系統測試提醒，用於驗證提醒功能是否正常運作。",
            recipient_email=recipient_email
            if notification_type == "email"
            else None,
            recipient_user_id=recipient_user_id
            if notification_type == "system"
            else None,
            status="pending",
        )

        reminder_service = ReminderService(db)
        success = await reminder_service.send_reminder(test_reminder)

        return {
            "success": success,
            "message": "測試提醒已發送" if success else "測試提醒發送失敗",
            "recipient": recipient_email
            if notification_type == "email"
            else f"User ID: {recipient_user_id}",
            "type": notification_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("發送測試提醒失敗: %s", e)
        raise HTTPException(
            status_code=500, detail="發送測試提醒失敗"
        )
