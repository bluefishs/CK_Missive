"""
公文行事曆模組 - 事件 CRUD API

包含端點：
- /events/list - 列出日曆事件
- /events - 新增日曆事件
- /events/create-with-reminders - 整合式建立事件
- /events/detail - 取得單一事件詳情
- /events/update - 更新日曆事件
- /events/delete - 刪除日曆事件
- /users/calendar-events - 獲取使用者的日曆事件
- /events/check-conflicts - 檢查事件時間衝突

@version 1.0.0
@date 2026-01-22
"""
from fastapi import APIRouter

from .common import (
    Depends, HTTPException, status,
    AsyncSession, select, or_, func, text,
    get_async_db, get_current_user,
    User, OfficialDocument, DocumentCalendarEvent, EventReminder,
    calendar_service,
    DocumentCalendarEventCreate, DocumentCalendarEventUpdate,
    EventListRequest, EventDetailRequest, EventDeleteRequest,
    UserEventsRequest, IntegratedEventCreate, ConflictCheckRequest,
    event_to_dict, check_event_permission, get_user_project_doc_ids,
    logger, datetime, timedelta
)

router = APIRouter()


@router.post("/events/list", summary="列出日曆事件")
async def list_calendar_events(
    request: EventListRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """列出當前使用者的日曆事件，支援篩選 (POST 機制)"""
    try:
        # 設定預設日期範圍
        if not request.start_date or not request.end_date:
            now = datetime.now()
            start_dt = now - timedelta(days=30)
            end_dt = now + timedelta(days=90)
        else:
            start_dt = datetime.fromisoformat(request.start_date)
            end_dt = datetime.fromisoformat(request.end_date)

        # 構建權限過濾條件
        if current_user.is_admin:
            permission_filter = True
        else:
            project_doc_ids = await get_user_project_doc_ids(db, current_user.id)

            permission_filter = or_(
                DocumentCalendarEvent.assigned_user_id == current_user.id,
                DocumentCalendarEvent.created_by == current_user.id
            )

            if project_doc_ids:
                permission_filter = or_(
                    permission_filter,
                    DocumentCalendarEvent.document_id.in_(project_doc_ids)
                )

        query = (
            select(DocumentCalendarEvent, OfficialDocument.doc_number)
            .outerjoin(OfficialDocument, DocumentCalendarEvent.document_id == OfficialDocument.id)
            .where(
                DocumentCalendarEvent.start_date >= start_dt,
                DocumentCalendarEvent.start_date <= end_dt,
                permission_filter
            )
        )

        # 應用篩選條件
        if request.event_type:
            query = query.where(DocumentCalendarEvent.event_type == request.event_type)
        if request.priority:
            query = query.where(DocumentCalendarEvent.priority == request.priority)
        if request.document_id:
            query = query.where(DocumentCalendarEvent.document_id == request.document_id)
        if request.keyword:
            keyword_filter = f"%{request.keyword}%"
            query = query.where(
                or_(
                    DocumentCalendarEvent.title.ilike(keyword_filter),
                    DocumentCalendarEvent.description.ilike(keyword_filter)
                )
            )

        # 分頁處理
        page = request.page or 1
        page_size = request.page_size or 50
        offset = (page - 1) * page_size

        # 取得總數
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 應用分頁和排序
        query = query.order_by(DocumentCalendarEvent.start_date.desc()).offset(offset).limit(page_size)
        result = await db.execute(query)
        events = result.all()

        return {
            "success": True,
            "events": [event_to_dict(event, doc_number) for event, doc_number in events],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    except Exception as e:
        logger.error(f"Error listing calendar events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出事件失敗: {str(e)}"
        )


@router.post("/events", summary="新增日曆事件")
async def create_calendar_event(
    event_create: DocumentCalendarEventCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """新增一個日曆事件"""
    try:
        # 處理時區問題
        start_date = event_create.start_date
        if start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)

        end_date = event_create.end_date
        if end_date and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        if not end_date:
            end_date = start_date + timedelta(hours=1)

        priority_str = str(event_create.priority) if event_create.priority else 'normal'

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

        return {
            "success": True,
            "message": "事件建立成功",
            "event": event_to_dict(new_event)
        }
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建立事件失敗: {str(e)}"
        )


@router.post("/events/create-with-reminders", summary="整合式建立事件 (含提醒與同步)")
async def create_event_with_reminders(
    request: IntegratedEventCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """整合式事件建立 - 一站完成事件建立、提醒設定、Google 同步"""
    try:
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
            detail=f"建立事件失敗: {str(e)}"
        )


@router.post("/events/detail", summary="取得單一事件詳情")
async def get_calendar_event(
    request: EventDetailRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """取得指定事件的詳細資訊"""
    event = await calendar_service.get_event(db, request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

    await check_event_permission(event, current_user, "查看")

    # 取得關聯公文資訊
    doc_number = None
    if event.document_id:
        doc_result = await db.execute(
            select(OfficialDocument.doc_number).where(OfficialDocument.id == event.document_id)
        )
        doc_number = doc_result.scalar_one_or_none()

    return {"success": True, "event": event_to_dict(event, doc_number)}


@router.post("/events/update", summary="更新日曆事件")
async def update_calendar_event(
    event_update: DocumentCalendarEventUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """更新一個已存在的日曆事件"""
    event_id = event_update.event_id

    event_to_update = await calendar_service.get_event(db, event_id)
    if not event_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

    await check_event_permission(event_to_update, current_user, "修改")

    updated_event = await calendar_service.update_event(db, event_id=event_id, event_update=event_update)
    if not updated_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="更新過程中找不到指定的事件")

    logger.info(f"使用者 {current_user.id} 更新日曆事件: {updated_event.title} (ID: {event_id})")

    return {
        "success": True,
        "message": "事件更新成功",
        "event": {
            "id": updated_event.id,
            "title": updated_event.title,
            "description": updated_event.description,
            "start_date": updated_event.start_date.isoformat(),
            "end_date": updated_event.end_date.isoformat() if updated_event.end_date else None,
            "all_day": updated_event.all_day,
            "event_type": updated_event.event_type,
            "priority": updated_event.priority,
            "updated_at": updated_event.updated_at.isoformat()
        }
    }


@router.post("/events/delete", summary="刪除日曆事件")
async def delete_calendar_event(
    request: EventDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """刪除一個日曆事件"""
    event = await calendar_service.get_event(db, request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

    # 權限檢查：只有建立者或管理員可以刪除
    if event.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您沒有權限刪除此事件")

    if not request.confirm:
        return {
            "success": False,
            "message": "請確認刪除操作",
            "event_title": event.title,
            "require_confirm": True
        }

    try:
        event_title = event.title
        await db.delete(event)
        await db.commit()

        logger.info(f"使用者 {current_user.id} 刪除日曆事件: {event_title} (ID: {request.event_id})")

        return {"success": True, "message": f"事件「{event_title}」已刪除"}
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除事件失敗: {str(e)}"
        )


@router.post("/users/calendar-events", summary="獲取使用者的日曆事件")
async def get_user_calendar_events(
    request: UserEventsRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取指定使用者的日曆事件"""
    try:
        if request.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己的日曆事件"
            )

        if not request.start_date or not request.end_date:
            now = datetime.now()
            start_dt = now - timedelta(days=30)
            end_dt = now + timedelta(days=60)
        else:
            start_dt = datetime.fromisoformat(request.start_date)
            end_dt = datetime.fromisoformat(request.end_date)

        query = (
            select(DocumentCalendarEvent, OfficialDocument.doc_number)
            .outerjoin(OfficialDocument, DocumentCalendarEvent.document_id == OfficialDocument.id)
            .where(
                DocumentCalendarEvent.start_date >= start_dt,
                DocumentCalendarEvent.start_date <= end_dt,
                or_(
                    DocumentCalendarEvent.assigned_user_id == request.user_id,
                    DocumentCalendarEvent.created_by == request.user_id
                )
            )
        )

        result = await db.execute(query)
        events = result.all()

        return {
            "success": True,
            "events": [event_to_dict(event, doc_number) for event, doc_number in events],
            "total": len(events),
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user calendar events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取使用者日曆事件失敗: {str(e)}"
        )


@router.post("/events/check-conflicts", summary="檢查事件時間衝突")
async def check_event_conflicts(
    request: ConflictCheckRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """檢查指定時間範圍是否與現有事件衝突"""
    try:
        start_time = datetime.fromisoformat(request.start_date)
        end_time = datetime.fromisoformat(request.end_date)

        conflicts = await calendar_service.detect_conflicts(
            db=db,
            start_time=start_time,
            end_time=end_time,
            exclude_event_id=request.exclude_event_id
        )

        return {
            "success": True,
            "has_conflicts": len(conflicts) > 0,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "message": f"偵測到 {len(conflicts)} 個時間衝突" if conflicts else "沒有時間衝突"
        }
    except Exception as e:
        logger.error(f"衝突檢查失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"衝突檢查失敗: {str(e)}"
        )
