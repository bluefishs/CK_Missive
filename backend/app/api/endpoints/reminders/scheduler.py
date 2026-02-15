"""
提醒排程器控制端點

@version 1.0.0
@date 2026-02-11
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)

from app.api.endpoints.auth import get_current_user
from app.extended.models import User
from app.services.reminder_scheduler import ReminderSchedulerController

router = APIRouter(prefix="/scheduler")


@router.post("/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user),
):
    """獲取提醒排程器狀態"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    return ReminderSchedulerController.get_scheduler_status()


@router.post("/start")
async def start_scheduler(
    current_user: User = Depends(get_current_user),
):
    """啟動提醒排程器"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        status = await ReminderSchedulerController.start_scheduler()
        return {"message": "排程器啟動成功", "status": status}
    except Exception as e:
        logger.error("啟動排程器失敗: %s", e)
        raise HTTPException(status_code=500, detail="啟動排程器失敗")


@router.post("/stop")
async def stop_scheduler(
    current_user: User = Depends(get_current_user),
):
    """停止提醒排程器"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        status = await ReminderSchedulerController.stop_scheduler()
        return {"message": "排程器停止成功", "status": status}
    except Exception as e:
        logger.error("停止排程器失敗: %s", e)
        raise HTTPException(status_code=500, detail="停止排程器失敗")


@router.post("/restart")
async def restart_scheduler(
    current_user: User = Depends(get_current_user),
):
    """重啟提醒排程器"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        status = await ReminderSchedulerController.restart_scheduler()
        return {"message": "排程器重啟成功", "status": status}
    except Exception as e:
        logger.error("重啟排程器失敗: %s", e)
        raise HTTPException(status_code=500, detail="重啟排程器失敗")


@router.post("/trigger")
async def trigger_manual_process(
    current_user: User = Depends(get_current_user),
):
    """手動觸發一次提醒處理"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="權限不足")

    try:
        result = await ReminderSchedulerController.trigger_manual_process()
        return result
    except Exception as e:
        logger.error("手動觸發失敗: %s", e)
        raise HTTPException(status_code=500, detail="手動觸發失敗")


@router.post("/interval")
async def update_check_interval(
    interval: int = Query(..., description="新的檢查間隔（秒）", ge=60),
    current_user: User = Depends(get_current_user),
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
        logger.error("更新檢查間隔失敗: %s", e)
        raise HTTPException(
            status_code=500, detail="更新檢查間隔失敗"
        )
