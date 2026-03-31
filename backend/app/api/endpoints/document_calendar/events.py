"""
公文行事曆模組 - 事件 CRUD API

包含端點：
- /events/list - 列出日曆事件
- /events/check-document - 檢查公文是否已有行事曆事件
- /events/detail - 取得單一事件詳情
- /events/update - 更新日曆事件
- /events/delete - 刪除日曆事件

建立端點已遷移至 events_create.py
批次/使用者/衝突端點已遷移至 events_batch.py

@version 1.1.0
@date 2026-03-30
"""
from fastapi import APIRouter

from .common import (
    Depends, HTTPException, status,
    AsyncSession, select, or_, func,
    get_async_db, get_current_user,
    User, OfficialDocument, DocumentCalendarEvent,
    calendar_service,
    DocumentCalendarEventUpdate,
    EventListRequest, EventDetailRequest, EventDeleteRequest,
    event_to_dict, check_event_permission, get_user_project_doc_ids,
    logger, datetime, timedelta
)
from app.schemas.document_calendar import CheckDocumentRequest
from app.extended.models import ContractProject
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.document_repository import DocumentRepository

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
            select(
                DocumentCalendarEvent,
                OfficialDocument.doc_number,
                ContractProject.project_name
            )
            .outerjoin(OfficialDocument, DocumentCalendarEvent.document_id == OfficialDocument.id)
            .outerjoin(ContractProject, OfficialDocument.contract_project_id == ContractProject.id)
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
            "events": [
                event_to_dict(event, doc_number, project_name)
                for event, doc_number, project_name in events
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
            detail="列出事件失敗，請稍後再試"
        )


@router.post("/events/check-document", summary="檢查公文是否已有行事曆事件")
async def check_document_events(
    request: CheckDocumentRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """檢查指定公文是否已有行事曆事件，用於前端提示"""
    try:
        cal_repo = CalendarRepository(db)
        existing_events = await cal_repo.get_events_by_document_ordered(request.document_id)

        if existing_events:
            return {
                "has_events": True,
                "event_count": len(existing_events),
                "events": [
                    {
                        "id": e.id,
                        "title": e.title,
                        "start_date": e.start_date.isoformat(),
                        "status": getattr(e, 'status', 'pending')
                    }
                    for e in existing_events
                ],
                "message": f"此公文已有 {len(existing_events)} 筆行事曆事件"
            }
        return {
            "has_events": False,
            "event_count": 0,
            "events": [],
            "message": "此公文尚無行事曆事件"
        }
    except Exception as e:
        logger.error(f"Error checking document events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="檢查公文事件失敗，請稍後再試"
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
        doc_repo = DocumentRepository(db)
        doc_data = await doc_repo.get_projected(event.document_id, ['doc_number'])
        doc_number = doc_data.get('doc_number') if doc_data else None

    return {"success": True, "event": event_to_dict(event, doc_number)}


@router.post("/events/update", summary="更新日曆事件")
async def update_calendar_event(
    event_update: DocumentCalendarEventUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """更新一個已存在的日曆事件"""
    try:
        event_id = event_update.event_id

        # 記錄收到的更新資料
        logger.info(f"[events/update] 收到更新請求: event_id={event_id}")
        logger.info(f"[events/update] 更新資料: {event_update.model_dump(exclude_unset=True)}")

        event_to_update = await calendar_service.get_event(db, event_id)
        if not event_to_update:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

        # 記錄原始事件資料
        logger.info(f"[events/update] 原始 start_date: {event_to_update.start_date}")

        await check_event_permission(event_to_update, current_user, "修改")

        updated_event = await calendar_service.update_event(db, event_id=event_id, event_update=event_update)
        if not updated_event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="更新過程中找不到指定的事件")

        # 記錄更新後的事件資料
        logger.info(f"[events/update] 更新後 start_date: {updated_event.start_date}")
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
                "updated_at": updated_event.updated_at.isoformat() if updated_event.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[events/update] 更新失敗: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新事件失敗，請稍後再試"
        )


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
            detail="刪除事件失敗，請稍後再試"
        )


