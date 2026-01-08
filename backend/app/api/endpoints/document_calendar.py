"""
公文行事曆整合 API 端點 (核心模組)
此為系統中唯一且統一的日曆事件 API 來源，並包含完整的 CRUD 功能
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, text, and_

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from ...extended.models import User, OfficialDocument, DocumentCalendarEvent
from ...services.document_calendar_service import DocumentCalendarService
from ...services.document_calendar_integrator import DocumentCalendarIntegrator
from app.schemas.document_calendar import (
    SyncStatusResponse,
    DocumentCalendarEventCreate,
    DocumentCalendarEventUpdate,
    DocumentCalendarEventResponse,
    EventListRequest,
    EventDetailRequest,
    EventDeleteRequest,
    EventSyncRequest,
    BulkSyncRequest,
    UserEventsRequest,
    IntegratedEventCreate,
    ReminderConfig
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

calendar_service = DocumentCalendarService()
calendar_integrator = DocumentCalendarIntegrator()

# ============================================================================
# 事件 CRUD 端點 (所有操作使用 POST 機制，符合資安要求)
# ============================================================================

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

        # 構建查詢 - 權限過濾邏輯:
        # 1. 事件建立者 (created_by)
        # 2. 事件指派者 (assigned_user_id)
        # 3. 事件關聯公文所屬專案的成員
        # 4. 管理員 (可看所有事件)

        # 構建權限過濾條件
        if current_user.is_admin:
            # 管理員可看所有事件
            permission_filter = True
        else:
            # 先取得使用者參與的專案 ID 列表
            project_ids_result = await db.execute(
                text("""
                    SELECT project_id FROM project_user_assignment
                    WHERE user_id = :user_id AND COALESCE(status, 'active') = 'active'
                """),
                {"user_id": current_user.id}
            )
            user_project_ids = [row.project_id for row in project_ids_result.fetchall()]

            # 基本權限過濾：建立者或指派者
            permission_filter = or_(
                DocumentCalendarEvent.assigned_user_id == current_user.id,
                DocumentCalendarEvent.created_by == current_user.id
            )

            # 如果使用者有參與專案，則也包含這些專案的事件
            if user_project_ids:
                # 取得這些專案關聯的公文 ID
                doc_ids_result = await db.execute(
                    text("""
                        SELECT id FROM documents
                        WHERE contract_project_id = ANY(:project_ids)
                    """),
                    {"project_ids": user_project_ids}
                )
                project_doc_ids = [row.id for row in doc_ids_result.fetchall()]

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

        # 應用分頁和排序 (降冪排序，最新事件優先)
        query = query.order_by(DocumentCalendarEvent.start_date.desc()).offset(offset).limit(page_size)
        result = await db.execute(query)
        events = result.all()

        return {
            "success": True,
            "events": [
                {
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
                    "google_event_id": getattr(event, 'google_event_id', None),
                    "google_sync_status": getattr(event, 'google_sync_status', None),
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                    "updated_at": event.updated_at.isoformat() if event.updated_at else None
                }
                for event, doc_number in events
            ],
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
        # 處理時區問題：將 timezone-aware datetime 轉換為 naive datetime
        # 資料庫使用 TIMESTAMP WITHOUT TIME ZONE
        start_date = event_create.start_date
        if start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)

        # 設定結束時間預設值
        end_date = event_create.end_date
        if end_date and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        if not end_date:
            end_date = start_date + timedelta(hours=1)

        # 建立事件 (使用現有 Model 欄位)
        # 注意：priority 在 Model 中是 String 類型
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
            "event": {
                "id": new_event.id,
                "title": new_event.title,
                "description": new_event.description,
                "start_date": new_event.start_date.isoformat(),
                "end_date": new_event.end_date.isoformat() if new_event.end_date else None,
                "all_day": new_event.all_day,
                "event_type": new_event.event_type,
                "priority": new_event.priority,
                "location": new_event.location,
                "document_id": new_event.document_id,
                "assigned_user_id": new_event.assigned_user_id,
                "created_by": new_event.created_by,
                "created_at": new_event.created_at.isoformat(),
                "updated_at": new_event.updated_at.isoformat()
            }
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
    """
    整合式事件建立 - 一站完成事件建立、提醒設定、Google 同步

    此端點用於從公文頁面直接建立完整的行事曆事件，無需分步操作。
    """
    from app.extended.models import EventReminder

    try:
        # 1. 處理時區：轉換為 naive datetime
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
        await db.flush()  # 取得 event.id 但不提交

        # 3. 建立提醒 (如果啟用)
        reminders_created = 0
        if request.reminder_enabled and request.reminders:
            for reminder_config in request.reminders:
                # 計算提醒時間
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

        # 5. Google Calendar 同步 (如果啟用)
        google_event_id = None
        if request.sync_to_google and calendar_service.is_ready():
            try:
                sync_result = await calendar_service.sync_event_to_google(
                    db=db,
                    event=new_event,
                    force=True
                )
                if sync_result.get('success'):
                    google_event_id = sync_result.get('google_event_id')
                    logger.info(f"事件已同步至 Google Calendar: {google_event_id}")
            except Exception as sync_error:
                logger.warning(f"Google 同步失敗，但事件已建立: {sync_error}")

        # 6. 發送專案成員通知 (非同步，不影響主流程)
        notifications_sent = 0
        try:
            from app.services.project_notification_service import ProjectNotificationService
            notification_service = ProjectNotificationService()
            notification_ids = await notification_service.send_calendar_event_notifications(
                db=db,
                event=new_event,
                exclude_user_id=current_user.id  # 排除建立者自己
            )
            notifications_sent = len(notification_ids)
            if notifications_sent > 0:
                logger.info(f"已發送 {notifications_sent} 則通知給專案成員")
        except Exception as notify_error:
            logger.warning(f"專案成員通知發送失敗 (不影響主流程): {notify_error}")

        logger.info(
            f"使用者 {current_user.id} 建立整合式事件: {new_event.title} "
            f"(ID: {new_event.id}, 提醒: {reminders_created}, Google: {bool(google_event_id)}, 通知: {notifications_sent})"
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
    """取得指定事件的詳細資訊 (POST 機制)"""
    event = await calendar_service.get_event(db, request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

    # 權限檢查
    if event.created_by != current_user.id and event.assigned_user_id != current_user.id:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您沒有權限查看此事件")

    # 取得關聯公文資訊
    doc_number = None
    if event.document_id:
        doc_result = await db.execute(
            select(OfficialDocument.doc_number).where(OfficialDocument.id == event.document_id)
        )
        doc_number = doc_result.scalar_one_or_none()

    return {
        "success": True,
        "event": {
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
            "google_event_id": getattr(event, 'google_event_id', None),
            "google_sync_status": getattr(event, 'google_sync_status', None),
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None
        }
    }


@router.post("/events/update", summary="更新日曆事件")
async def update_calendar_event(
    event_update: DocumentCalendarEventUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """更新一個已存在的日曆事件 (POST 機制)"""
    event_id = event_update.event_id

    # 權限檢查：確保只有事件的建立者或負責人可以修改
    event_to_update = await calendar_service.get_event(db, event_id)
    if not event_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

    if event_to_update.created_by != current_user.id and event_to_update.assigned_user_id != current_user.id:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您沒有權限修改此事件")

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
    """刪除一個日曆事件 (POST 機制)"""
    # 取得事件
    event = await calendar_service.get_event(db, request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

    # 權限檢查：只有建立者或管理員可以刪除
    if event.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您沒有權限刪除此事件")

    # 安全確認
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

        return {
            "success": True,
            "message": f"事件「{event_title}」已刪除"
        }
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除事件失敗: {str(e)}"
        )


@router.post("/events/sync", summary="同步事件至 Google Calendar")
async def sync_event_to_google(
    request: EventSyncRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """同步指定事件至 Google Calendar (POST 機制)"""
    # 取得事件
    event = await calendar_service.get_event(db, request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

    # 權限檢查
    if event.created_by != current_user.id and event.assigned_user_id != current_user.id:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您沒有權限同步此事件")

    # 檢查 Google Calendar 服務是否可用
    if not calendar_service.is_ready():
        return {
            "success": False,
            "message": "Google Calendar 服務未配置或不可用",
            "google_event_id": None
        }

    try:
        # 呼叫實際的 Google Calendar 同步服務
        result = await calendar_service.sync_event_to_google(
            db=db,
            event=event,
            force=request.force_sync
        )

        return {
            "success": result['success'],
            "message": result['message'],
            "google_event_id": result.get('google_event_id')
        }
    except Exception as e:
        logger.error(f"Error syncing event to Google: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步失敗: {str(e)}"
        )


@router.post("/events/bulk-sync", summary="批次同步事件至 Google Calendar")
async def bulk_sync_events_to_google(
    request: BulkSyncRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    批次同步事件至 Google Calendar (POST 機制)

    - 若提供 event_ids，則同步指定的事件
    - 若 sync_all_pending=True 且未提供 event_ids，則同步所有未同步的事件
    """
    if not calendar_service.is_ready():
        return {
            "success": False,
            "message": "Google Calendar 服務未配置或不可用",
            "synced_count": 0,
            "failed_count": 0
        }

    try:
        result = await calendar_service.bulk_sync_to_google(
            db=db,
            event_ids=request.event_ids,
            sync_all_pending=request.sync_all_pending if not request.event_ids else False
        )
        return result
    except Exception as e:
        logger.error(f"批次同步失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批次同步失敗: {str(e)}"
        )


@router.post("/users/calendar-events", summary="獲取使用者的日曆事件")
async def get_user_calendar_events(
    request: UserEventsRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取指定使用者的日曆事件 (POST 機制)"""
    try:
        # 權限檢查：只能查看自己的事件（除非是管理員）
        if request.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己的日曆事件"
            )

        # 設定預設日期範圍
        if not request.start_date or not request.end_date:
            now = datetime.now()
            start_dt = now - timedelta(days=30)
            end_dt = now + timedelta(days=60)
        else:
            start_dt = datetime.fromisoformat(request.start_date)
            end_dt = datetime.fromisoformat(request.end_date)

        # 查詢使用者相關的日曆事件
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
            "success": True,
            "events": calendar_events,
            "total": len(calendar_events),
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

# ============================================================================
# 統計與分類端點 (整合自 pure_calendar.py)
# ============================================================================

@router.get("/stats", summary="獲取行事曆統計資料")
async def get_calendar_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取行事曆統計資料"""
    try:
        now = datetime.now()

        # 總事件數
        total_query = select(func.count(DocumentCalendarEvent.id)).where(
            or_(
                DocumentCalendarEvent.assigned_user_id == current_user.id,
                DocumentCalendarEvent.created_by == current_user.id
            )
        )
        total_events = (await db.execute(total_query)).scalar() or 0

        # 今日事件
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        today_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date >= today_start,
            DocumentCalendarEvent.start_date < today_end,
            or_(
                DocumentCalendarEvent.assigned_user_id == current_user.id,
                DocumentCalendarEvent.created_by == current_user.id
            )
        )
        today_events = (await db.execute(today_query)).scalar() or 0

        # 本週事件
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        week_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date >= week_start,
            DocumentCalendarEvent.start_date < week_end,
            or_(
                DocumentCalendarEvent.assigned_user_id == current_user.id,
                DocumentCalendarEvent.created_by == current_user.id
            )
        )
        week_events = (await db.execute(week_query)).scalar() or 0

        # 本月事件
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        month_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date >= month_start,
            DocumentCalendarEvent.start_date < next_month,
            or_(
                DocumentCalendarEvent.assigned_user_id == current_user.id,
                DocumentCalendarEvent.created_by == current_user.id
            )
        )
        month_events = (await db.execute(month_query)).scalar() or 0

        # 即將到來事件
        upcoming_query = select(func.count(DocumentCalendarEvent.id)).where(
            DocumentCalendarEvent.start_date > now,
            or_(
                DocumentCalendarEvent.assigned_user_id == current_user.id,
                DocumentCalendarEvent.created_by == current_user.id
            )
        )
        upcoming_events = (await db.execute(upcoming_query)).scalar() or 0

        return {
            "total_events": total_events,
            "today_events": today_events,
            "this_week_events": week_events,
            "this_month_events": month_events,
            "upcoming_events": upcoming_events
        }

    except Exception as e:
        logger.error(f"Error getting calendar stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取統計資料失敗: {str(e)}"
        )


@router.get("/categories", summary="獲取行事曆事件分類")
async def get_calendar_categories(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取行事曆事件分類"""
    try:
        # 預設分類定義
        default_categories = [
            {"value": "reminder", "label": "提醒", "color": "#faad14"},
            {"value": "deadline", "label": "截止日期", "color": "#f5222d"},
            {"value": "meeting", "label": "會議", "color": "#722ed1"},
            {"value": "review", "label": "審查", "color": "#1890ff"},
        ]

        # 查詢資料庫中實際使用的事件類型
        event_types_query = select(DocumentCalendarEvent.event_type).distinct()
        event_types_result = await db.execute(event_types_query)
        db_event_types = event_types_result.scalars().all()

        # 合併預設分類和資料庫中的類型
        existing_values = {cat["value"] for cat in default_categories}
        for event_type in db_event_types:
            if event_type and event_type not in existing_values:
                default_categories.append({
                    "value": event_type,
                    "label": event_type,
                    "color": "#1890ff"
                })

        return {"categories": default_categories}

    except Exception as e:
        logger.error(f"Error getting calendar categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取分類失敗: {str(e)}"
        )


@router.get("/status", summary="獲取行事曆服務狀態")
async def get_calendar_status():
    """獲取行事曆服務狀態"""
    return {
        "calendar_available": True,
        "message": "行事曆服務運作正常",
        "service_type": "integrated",
        "features": ["本地行事曆", "事件提醒", "公文關聯"]
    }


@router.get("/google-events", summary="列出 Google Calendar 事件（測試用）")
async def list_google_events():
    """直接從 Google Calendar 讀取事件，用於驗證同步結果"""
    if not calendar_service.is_ready():
        return {
            "success": False,
            "message": "Google Calendar 服務未就緒",
            "calendar_id": calendar_service.calendar_id,
            "events": []
        }

    try:
        events_result = calendar_service.service.events().list(
            calendarId=calendar_service.calendar_id,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return {
            "success": True,
            "calendar_id": calendar_service.calendar_id,
            "event_count": len(events),
            "events": [
                {
                    "id": e.get("id"),
                    "summary": e.get("summary", "無標題"),
                    "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                    "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                }
                for e in events
            ]
        }
    except Exception as e:
        logger.error(f"讀取 Google Calendar 事件失敗: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
            "calendar_id": calendar_service.calendar_id,
            "events": []
        }


# ============================================================================
# 衝突偵測端點
# ============================================================================

class ConflictCheckRequest(BaseModel):
    """衝突檢查請求"""
    start_date: str  # ISO format datetime
    end_date: str    # ISO format datetime
    exclude_event_id: Optional[int] = None


@router.post("/events/check-conflicts", summary="檢查事件時間衝突")
async def check_event_conflicts(
    request: ConflictCheckRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    檢查指定時間範圍是否與現有事件衝突

    用於新增或編輯事件前的衝突預警
    """
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


# ============================================================================
# Google Calendar 同步排程器控制端點
# ============================================================================

from app.services.google_sync_scheduler import GoogleSyncSchedulerController


@router.get("/sync-scheduler/status", summary="取得同步排程器狀態")
async def get_sync_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """取得 Google Calendar 同步排程器的運行狀態"""
    return GoogleSyncSchedulerController.get_scheduler_status()


@router.post("/sync-scheduler/start", summary="啟動同步排程器")
async def start_sync_scheduler(
    current_user: User = Depends(get_current_user)
):
    """啟動 Google Calendar 自動同步排程器（需管理員權限）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理員可以控制排程器"
        )
    return await GoogleSyncSchedulerController.start_scheduler()


@router.post("/sync-scheduler/stop", summary="停止同步排程器")
async def stop_sync_scheduler(
    current_user: User = Depends(get_current_user)
):
    """停止 Google Calendar 自動同步排程器（需管理員權限）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理員可以控制排程器"
        )
    return await GoogleSyncSchedulerController.stop_scheduler()


@router.post("/sync-scheduler/trigger", summary="手動觸發同步")
async def trigger_manual_sync(
    current_user: User = Depends(get_current_user)
):
    """手動觸發一次 Google Calendar 同步"""
    return await GoogleSyncSchedulerController.trigger_manual_sync()


class SyncIntervalRequest(BaseModel):
    """同步間隔設定請求"""
    interval_seconds: int  # 最小 60 秒


@router.post("/sync-scheduler/set-interval", summary="設定同步間隔")
async def set_sync_interval(
    request: SyncIntervalRequest,
    current_user: User = Depends(get_current_user)
):
    """設定自動同步間隔（需管理員權限）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理員可以修改同步設定"
        )
    try:
        return await GoogleSyncSchedulerController.update_sync_interval(request.interval_seconds)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )