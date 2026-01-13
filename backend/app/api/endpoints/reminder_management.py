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


class ReminderActionRequest(BaseModel):
    """提醒操作請求 (新增/刪除)"""
    action: str  # 'add' or 'delete'
    reminder_type: Optional[str] = "system"
    reminder_minutes: Optional[int] = 60
    reminder_time: Optional[str] = None
    reminder_id: Optional[int] = None

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

@router.post("/events/{event_id}/reminders", response_model=ReminderStatusResponse)
async def get_event_reminders_status(
    event_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取特定事件的提醒狀態 (支援 GET 和 POST)"""
    try:
        from sqlalchemy import select
        from app.extended.models import EventReminder

        # 直接查詢提醒列表
        result = await db.execute(
            select(EventReminder).where(EventReminder.event_id == event_id)
        )
        reminders = result.scalars().all()

        # 統計狀態
        by_status = {}
        reminder_list = []
        for r in reminders:
            status = r.status or 'pending'
            by_status[status] = by_status.get(status, 0) + 1
            reminder_list.append({
                "id": r.id,
                "event_id": r.event_id,
                "reminder_minutes": getattr(r, 'reminder_minutes', 60),
                "reminder_time": r.reminder_time.isoformat() if r.reminder_time else None,
                "reminder_type": r.notification_type or r.reminder_type or 'system',
                "notification_type": r.notification_type,
                "title": getattr(r, 'title', None),
                "status": r.status or 'pending',
                "is_sent": getattr(r, 'is_sent', False),
                "retry_count": getattr(r, 'retry_count', 0),
                "priority": getattr(r, 'priority', 3),
                "message": getattr(r, 'message', None)
            })

        return {
            "success": True,
            "total": len(reminders),
            "by_status": by_status,
            "reminders": reminder_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取提醒狀態失敗: {str(e)}")

@router.post("/documents/{document_id}/reminders", response_model=Dict[str, Any])
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
    request: ReminderActionRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """新增或刪除事件的提醒"""
    try:
        from datetime import datetime
        from app.extended.models import EventReminder, DocumentCalendarEvent
        from sqlalchemy import select

        # 獲取事件
        event_result = await db.execute(
            select(DocumentCalendarEvent).where(DocumentCalendarEvent.id == event_id)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="找不到指定的事件")

        if request.action == 'add':
            # 新增提醒
            reminder_time = None
            if request.reminder_time:
                reminder_time = datetime.fromisoformat(request.reminder_time.replace('Z', '+00:00'))
            elif event.start_date and request.reminder_minutes:
                from datetime import timedelta
                reminder_time = event.start_date - timedelta(minutes=request.reminder_minutes)

            new_reminder = EventReminder(
                event_id=event_id,
                reminder_minutes=request.reminder_minutes or 60,
                reminder_time=reminder_time,
                notification_type=request.reminder_type or 'system',
                title=f"事件提醒: {event.title}",
                message=f"您有一個即將到來的事件: {event.title}",
                recipient_user_id=current_user.id,
                status='pending',
                priority=3
            )
            db.add(new_reminder)
            await db.commit()
            await db.refresh(new_reminder)

            return {
                "success": True,
                "message": "提醒已新增",
                "reminder_id": new_reminder.id
            }

        elif request.action == 'delete':
            # 刪除提醒
            if not request.reminder_id:
                raise HTTPException(status_code=400, detail="刪除操作需要提供 reminder_id")

            reminder_result = await db.execute(
                select(EventReminder).where(
                    EventReminder.id == request.reminder_id,
                    EventReminder.event_id == event_id
                )
            )
            reminder = reminder_result.scalar_one_or_none()
            if not reminder:
                raise HTTPException(status_code=404, detail="找不到指定的提醒")

            await db.delete(reminder)
            await db.commit()

            return {
                "success": True,
                "message": "提醒已刪除"
            }

        else:
            raise HTTPException(status_code=400, detail=f"不支援的操作: {request.action}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失敗: {str(e)}")

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

@router.post("/pending-count")
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

@router.post("/templates/defaults")
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

@router.post("/statistics")
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

@router.post("/scheduler/status")
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

@router.post("/scheduler/interval")
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