"""
公文行事曆模組 - 批次操作 / 使用者事件 / 衝突檢查 API

包含端點：
- /events/batch-update-status - 批次更新事件狀態
- /events/batch-delete - 批次刪除事件
- /users/calendar-events - 獲取使用者的日曆事件
- /events/check-conflicts - 檢查事件時間衝突

拆分自 events.py (v1.0.0)

@version 1.0.0
@date 2026-03-30
"""
from fastapi import APIRouter

from .common import (
    Depends, HTTPException, status,
    AsyncSession, select, or_, and_,
    get_async_db, get_current_user,
    User, OfficialDocument, DocumentCalendarEvent,
    calendar_service,
    UserEventsRequest, ConflictCheckRequest,
    event_to_dict,
    logger, datetime, timedelta
)
from app.schemas.document_calendar import BatchUpdateStatusRequest, BatchDeleteRequest
from app.extended.models import ContractProject

router = APIRouter()


@router.post("/events/batch-update-status", summary="批次更新事件狀態")
async def batch_update_event_status(
    request: BatchUpdateStatusRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """批次更新多個事件的狀態（單次 DB 操作，避免 rate limit）"""
    try:
        if request.status not in ('pending', 'completed', 'cancelled'):
            raise HTTPException(status_code=422, detail="無效的狀態值")

        result = await calendar_service.batch_update_status(db, request.event_ids, request.status)
        logger.info(f"使用者 {current_user.id} 批次更新 {result['updated']} 個事件為 {request.status}")
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批次更新事件狀態失敗: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="批次更新失敗")


@router.post("/events/batch-delete", summary="批次刪除事件")
async def batch_delete_events(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """批次刪除多個事件（單次 DB 操作）"""
    try:
        result = await calendar_service.batch_delete(db, request.event_ids)
        logger.info(f"使用者 {current_user.id} 批次刪除 {result['deleted']} 個事件")
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"批次刪除事件失敗: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="批次刪除失敗")


@router.post("/users/calendar-events", summary="獲取使用者的日曆事件")
async def get_user_calendar_events(
    request: UserEventsRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """獲取指定使用者的日曆事件（含承攬案件名稱）"""
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

        # 查詢事件，同時 JOIN 公文和承攬案件以取得案件名稱
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
                or_(
                    DocumentCalendarEvent.assigned_user_id == request.user_id,
                    DocumentCalendarEvent.created_by == request.user_id,
                    # 包含無指派使用者的公共事件（公文匯入自動建立）
                    and_(
                        DocumentCalendarEvent.assigned_user_id.is_(None),
                        DocumentCalendarEvent.created_by.is_(None)
                    )
                )
            )
        )

        result = await db.execute(query)
        events = result.all()

        return {
            "success": True,
            "events": [
                event_to_dict(event, doc_number, project_name)
                for event, doc_number, project_name in events
            ],
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
            detail="獲取使用者日曆事件失敗，請稍後再試"
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
            detail="衝突檢查失敗，請稍後再試"
        )
