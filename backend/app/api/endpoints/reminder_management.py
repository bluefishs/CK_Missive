"""
提醒管理API端點
管理行事曆事件的多層級提醒
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.services.document_calendar_integrator import DocumentCalendarIntegrator
from app.services.reminder_service import ReminderService
from app.services.reminder_scheduler import ReminderSchedulerController
from app.extended.models import User

router = APIRouter()

class ReminderTemplateConfig(BaseModel):
    """提醒模板配置"""
    minutes: int
    type: str = "email"  # email/system（內部系統訊息）
    priority: int = 3
    title: Optional[str] = None

class CustomReminderTemplate(BaseModel):
    """自訂提醒模板"""
    event_id: int
    template: List[ReminderTemplateConfig]

class ReminderStatusResponse(BaseModel):
    """提醒狀態回應"""
    total: int
    by_status: Dict[str, int]
    reminders: List[Dict[str, Any]]

class BatchProcessResponse(BaseModel):
    """批量處理回應"""
    total: int
    sent: int
    failed: int
    retries: int

# 初始化服務
calendar_integrator = DocumentCalendarIntegrator()
reminder_service = ReminderService()

@router.get("/events/{event_id}/reminders", response_model=ReminderStatusResponse)
async def get_event_reminders_status(
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取特定事件的提醒狀態"""
    try:
        status = await calendar_integrator.get_reminder_status(
            db=db,
            event_id=event_id
        )

        if "error" in status:
            raise HTTPException(status_code=400, detail=status["error"])

        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取提醒狀態失敗: {str(e)}")

@router.get("/documents/{document_id}/reminders", response_model=Dict[str, Any])
async def get_document_reminders_status(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取公文所有事件的提醒狀態"""
    try:
        status = await calendar_integrator.get_reminder_status(
            db=db,
            document_id=document_id
        )

        if "error" in status:
            raise HTTPException(status_code=400, detail=status["error"])

        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取公文提醒狀態失敗: {str(e)}")

@router.post("/events/{event_id}/reminders/update-template")
async def update_event_reminder_template(
    event_id: int,
    template_config: List[ReminderTemplateConfig],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """更新事件的提醒模板"""
    try:
        # 轉換為服務所需的格式
        template = [
            {
                "minutes": config.minutes,
                "type": config.type,
                "priority": config.priority,
                "title": config.title or f"事件提醒 - {config.type}"
            }
            for config in template_config
        ]

        success = await reminder_service.update_reminder_template(
            db=db,
            event_id=event_id,
            new_template=template
        )

        if not success:
            raise HTTPException(status_code=400, detail="更新提醒模板失敗")

        return {"message": "提醒模板更新成功", "event_id": event_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新提醒模板失敗: {str(e)}")

@router.post("/process-pending", response_model=BatchProcessResponse)
async def process_pending_reminders(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """批量處理待發送的提醒"""
    try:
        # 僅管理員可以執行此操作
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="權限不足")

        stats = await calendar_integrator.process_pending_reminders(db)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"處理提醒失敗: {str(e)}")

@router.get("/pending-count")
async def get_pending_reminders_count(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取待處理提醒數量"""
    try:
        pending_reminders = await reminder_service.get_pending_reminders(db)
        return {
            "count": len(pending_reminders),
            "reminders": [
                {
                    "id": reminder.id,
                    "event_id": reminder.event_id,
                    "reminder_time": reminder.reminder_time.isoformat(),
                    "notification_type": reminder.notification_type,
                    "priority": reminder.priority,
                    "retry_count": reminder.retry_count
                }
                for reminder in pending_reminders[:20]  # 只返回前20個
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取待處理提醒失敗: {str(e)}")

@router.get("/templates/defaults")
async def get_default_reminder_templates(
    current_user: User = Depends(get_current_user)
):
    """獲取預設提醒模板"""
    return {
        "templates": reminder_service.DEFAULT_REMINDER_TEMPLATES,
        "description": "預設提醒模板配置，可作為自訂模板的參考"
    }

@router.post("/send-test-reminder")
async def send_test_reminder(
    recipient_email: Optional[str] = Query(None, description="測試收件人信箱（email類型時必填）"),
    recipient_user_id: Optional[int] = Query(None, description="測試收件人ID（system類型時必填）"),
    notification_type: str = Query("email", description="通知類型（email/system）"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """發送測試提醒（僅管理員）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="權限不足")

        # 驗證通知類型
        if notification_type not in ["email", "system"]:
            raise HTTPException(status_code=400, detail="不支援的通知類型，僅支援 email 和 system")

        # 驗證必要參數
        if notification_type == "email" and not recipient_email:
            raise HTTPException(status_code=400, detail="email類型提醒需要提供收件人信箱")

        if notification_type == "system" and not recipient_user_id:
            raise HTTPException(status_code=400, detail="system類型提醒需要提供收件人用戶ID")

        # 創建測試提醒對象
        from app.extended.models import EventReminder
        from datetime import datetime

        test_reminder = EventReminder(
            event_id=0,  # 測試用
            reminder_minutes=0,
            reminder_time=datetime.now(),
            notification_type=notification_type,
            title="系統測試提醒",
            message="這是一則系統測試提醒，用於驗證提醒功能是否正常運作。",
            recipient_email=recipient_email if notification_type == "email" else None,
            recipient_user_id=recipient_user_id if notification_type == "system" else None,
            status="pending"
        )

        # 發送測試提醒
        success = await reminder_service.send_reminder(db, test_reminder)

        return {
            "success": success,
            "message": "測試提醒已發送" if success else "測試提醒發送失敗",
            "recipient": recipient_email if notification_type == "email" else f"User ID: {recipient_user_id}",
            "type": notification_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"發送測試提醒失敗: {str(e)}")

@router.get("/statistics")
async def get_reminder_statistics(
    days: int = Query(30, description="統計天數"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取提醒統計資訊"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, and_
        from app.extended.models import EventReminder

        # 計算統計期間
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 查詢統計數據
        result = await db.execute(
            db.query(
                EventReminder.status,
                EventReminder.notification_type,
                func.count(EventReminder.id).label('count')
            )
            .where(
                and_(
                    EventReminder.created_at >= start_date,
                    EventReminder.created_at <= end_date
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
            "statistics": statistics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取統計資訊失敗: {str(e)}")

# --- 排程器控制 API ---

@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """獲取提醒排程器狀態"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    return ReminderSchedulerController.get_scheduler_status()

@router.post("/scheduler/start")
async def start_scheduler(
    current_user: User = Depends(get_current_user)
):
    """啟動提醒排程器"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        status = await ReminderSchedulerController.start_scheduler()
        return {"message": "排程器啟動成功", "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"啟動排程器失敗: {str(e)}")

@router.post("/scheduler/stop")
async def stop_scheduler(
    current_user: User = Depends(get_current_user)
):
    """停止提醒排程器"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        status = await ReminderSchedulerController.stop_scheduler()
        return {"message": "排程器停止成功", "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止排程器失敗: {str(e)}")

@router.post("/scheduler/restart")
async def restart_scheduler(
    current_user: User = Depends(get_current_user)
):
    """重啟提醒排程器"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        status = await ReminderSchedulerController.restart_scheduler()
        return {"message": "排程器重啟成功", "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重啟排程器失敗: {str(e)}")

@router.post("/scheduler/trigger")
async def trigger_manual_process(
    current_user: User = Depends(get_current_user)
):
    """手動觸發一次提醒處理"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        result = await ReminderSchedulerController.trigger_manual_process()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"手動觸發失敗: {str(e)}")

@router.put("/scheduler/interval")
async def update_check_interval(
    interval: int = Query(..., description="新的檢查間隔（秒）", ge=60),
    current_user: User = Depends(get_current_user)
):
    """更新排程器檢查間隔"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        result = await ReminderSchedulerController.update_check_interval(interval)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新檢查間隔失敗: {str(e)}")