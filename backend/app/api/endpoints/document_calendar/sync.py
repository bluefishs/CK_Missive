"""
公文行事曆模組 - Google Calendar 同步 API

包含端點：
- /events/sync - 同步單一事件至 Google Calendar
- /events/bulk-sync - 批次同步事件至 Google Calendar
- /google-events - 列出 Google Calendar 事件（測試用）

@version 1.0.0
@date 2026-01-22
"""
from fastapi import APIRouter

from .common import (
    Depends, HTTPException, status,
    AsyncSession,
    get_async_db, get_current_user,
    User,
    calendar_service,
    EventSyncRequest, BulkSyncRequest,
    check_event_permission,
    logger
)

router = APIRouter()


@router.post("/events/sync", summary="同步事件至 Google Calendar")
async def sync_event_to_google(
    request: EventSyncRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """同步指定事件至 Google Calendar"""
    event = await calendar_service.get_event(db, request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的事件")

    await check_event_permission(event, current_user, "同步")

    if not calendar_service.is_ready():
        return {
            "success": False,
            "message": "Google Calendar 服務未配置或不可用",
            "google_event_id": None
        }

    try:
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
    批次同步事件至 Google Calendar

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


@router.post("/google-events", summary="列出 Google Calendar 事件（測試用）")
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
