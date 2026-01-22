"""
公文行事曆模組 - 同步排程器控制 API

包含端點：
- /sync-scheduler/status - 取得同步排程器狀態
- /sync-scheduler/start - 啟動同步排程器
- /sync-scheduler/stop - 停止同步排程器
- /sync-scheduler/trigger - 手動觸發同步
- /sync-scheduler/set-interval - 設定同步間隔

@version 1.0.0
@date 2026-01-22
"""
from fastapi import APIRouter

from .common import (
    Depends, HTTPException, status,
    get_current_user,
    User,
    SyncIntervalRequest
)
from app.services.google_sync_scheduler import GoogleSyncSchedulerController

router = APIRouter()


@router.post("/sync-scheduler/status", summary="取得同步排程器狀態")
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
