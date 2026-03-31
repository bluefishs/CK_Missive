"""
公文行事曆模組 - 事件建立 API

包含端點：
- /events - 新增日曆事件
- /events/create-with-reminders - 整合式建立事件 (含提醒與同步)

拆分自 events.py (v1.1.0)

@version 1.0.0
@date 2026-03-30
"""
from fastapi import APIRouter

from .common import (
    Depends, HTTPException, status,
    AsyncSession,
    get_async_db, get_current_user,
    User, DocumentCalendarEvent, EventReminder,
    calendar_service,
    DocumentCalendarEventCreate, IntegratedEventCreate,
    event_to_dict,
    logger, timedelta
)
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.document_repository import DocumentRepository

router = APIRouter()


@router.post("/events", summary="新增日曆事件")
async def create_calendar_event(
    event_create: DocumentCalendarEventCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """新增一個日曆事件

    document_id 為選填，不提供時建立獨立事件
    """
    try:
        doc_repo = DocumentRepository(db)
        cal_repo = CalendarRepository(db)

        existing_event_warning = None

        # 僅在提供 document_id 時驗證公文存在與重複事件
        if event_create.document_id is not None:
            if not await doc_repo.exists(event_create.document_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"找不到公文 ID: {event_create.document_id}"
                )

            # 檢查重複事件（相同公文+相同標題+相同日期）
            start_date_only = event_create.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date_only = start_date_only + timedelta(days=1)

            existing_duplicate = await cal_repo.find_duplicate_event(
                event_create.document_id, event_create.title,
                start_date_only, end_date_only
            )
            if existing_duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"此公文在同一天已有相同標題的事件 (ID: {existing_duplicate.id})"
                )

            # 檢查公文是否已有事件（提供警告但不阻擋建立）
            existing_count = await cal_repo.count_by_document(event_create.document_id)
            if existing_count > 0:
                existing_event_warning = f"注意：此公文已有 {existing_count} 筆行事曆事件"
                logger.info(f"公文 {event_create.document_id} 已有 {existing_count} 筆事件，仍建立新事件")

        # 處理時區問題
        start_date = event_create.start_date
        if start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)

        end_date = event_create.end_date
        if end_date and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        if not end_date:
            end_date = start_date + timedelta(hours=1)

        priority_str = str(event_create.priority) if event_create.priority else '3'  # 統一預設為普通優先級

        new_event = DocumentCalendarEvent(
            title=event_create.title,
            description=event_create.description,
            start_date=start_date,
            end_date=end_date,
            all_day=event_create.all_day or False,
            event_type=event_create.event_type or 'reminder',
            priority=priority_str,
            location=event_create.location,
            document_id=event_create.document_id,
            assigned_user_id=event_create.assigned_user_id or current_user.id,
            created_by=current_user.id
        )

        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)

        logger.info(f"使用者 {current_user.id} 建立日曆事件: {new_event.title} (ID: {new_event.id})")

        response = {
            "success": True,
            "message": "事件建立成功",
            "event": event_to_dict(new_event)
        }
        if existing_event_warning:
            response["warning"] = existing_event_warning

        return response
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="建立事件失敗，請稍後再試"
        )


@router.post("/events/create-with-reminders", summary="整合式建立事件 (含提醒與同步)")
async def create_event_with_reminders(
    request: IntegratedEventCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """整合式事件建立 - 一站完成事件建立、提醒設定、Google 同步

    document_id 為選填，不提供時建立獨立事件
    """
    try:
        doc_repo = DocumentRepository(db)
        cal_repo = CalendarRepository(db)

        # 0. 僅在提供 document_id 時驗證公文存在
        if request.document_id is not None:
            if not await doc_repo.exists(request.document_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"找不到公文 ID: {request.document_id}"
                )

        # 1. 處理時區
        start_date = request.start_date
        if start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)

        end_date = request.end_date
        if end_date:
            if end_date.tzinfo is not None:
                end_date = end_date.replace(tzinfo=None)
        else:
            end_date = start_date + timedelta(hours=1)

        # 1.5. 檢查重複事件（僅關聯公文時檢查：相同公文+相同標題+相同日期）
        if request.document_id is not None:
            start_date_only = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date_only = start_date_only + timedelta(days=1)

            existing_duplicate = await cal_repo.find_duplicate_event(
                request.document_id, request.title,
                start_date_only, end_date_only
            )
            if existing_duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"此公文在同一天已有相同標題的事件 (ID: {existing_duplicate.id})"
                )

        # 2. 建立事件
        priority_str = str(request.priority) if request.priority else '3'

        new_event = DocumentCalendarEvent(
            title=request.title,
            description=request.description,
            start_date=start_date,
            end_date=end_date,
            all_day=request.all_day,
            event_type=request.event_type,
            priority=priority_str,
            location=request.location,
            document_id=request.document_id,
            assigned_user_id=current_user.id,
            created_by=current_user.id
        )

        db.add(new_event)
        await db.flush()

        # 3. 建立提醒
        reminders_created = 0
        if request.reminder_enabled and request.reminders:
            for reminder_config in request.reminders:
                reminder_time = start_date - timedelta(minutes=reminder_config.minutes_before)

                new_reminder = EventReminder(
                    event_id=new_event.id,
                    reminder_minutes=reminder_config.minutes_before,
                    reminder_time=reminder_time,
                    notification_type=reminder_config.notification_type,
                    reminder_type=reminder_config.notification_type,
                    title=f"事件提醒: {request.title}",
                    message=f"您有一個即將到來的事件: {request.title}",
                    recipient_user_id=current_user.id,
                    status='pending',
                    priority=3
                )
                db.add(new_reminder)
                reminders_created += 1

        # 4. 提交事務
        await db.commit()
        await db.refresh(new_event)

        # 5. Google Calendar 同步
        google_event_id = None
        if request.sync_to_google and calendar_service.is_ready():
            try:
                sync_result = await calendar_service.sync_event_to_google(
                    db=db, event=new_event, force=True
                )
                if sync_result.get('success'):
                    google_event_id = sync_result.get('google_event_id')
                    logger.info(f"事件已同步至 Google Calendar: {google_event_id}")
            except Exception as sync_error:
                logger.warning(f"Google 同步失敗，但事件已建立: {sync_error}")

        # 6. 發送專案成員通知
        notifications_sent = 0
        try:
            from app.services.project_notification_service import ProjectNotificationService
            notification_service = ProjectNotificationService()
            notification_ids = await notification_service.send_calendar_event_notifications(
                db=db, event=new_event, exclude_user_id=current_user.id
            )
            notifications_sent = len(notification_ids)
        except Exception as notify_error:
            logger.warning(f"專案成員通知發送失敗: {notify_error}")

        logger.info(
            f"使用者 {current_user.id} 建立整合式事件: {new_event.title} "
            f"(ID: {new_event.id}, 提醒: {reminders_created}, Google: {bool(google_event_id)})"
        )

        return {
            "success": True,
            "message": "事件建立成功",
            "event_id": new_event.id,
            "reminders_created": reminders_created,
            "notifications_sent": notifications_sent,
            "google_event_id": google_event_id,
            "event": {
                "id": new_event.id,
                "title": new_event.title,
                "start_date": new_event.start_date.isoformat(),
                "end_date": new_event.end_date.isoformat() if new_event.end_date else None,
                "event_type": new_event.event_type,
                "document_id": new_event.document_id
            }
        }

    except Exception as e:
        logger.error(f"整合式事件建立失敗: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="建立事件失敗，請稍後再試"
        )
