# -*- coding: utf-8 -*-
"""
任務排程器

提供定時任務排程功能，用於：
- 處理待發送提醒
- 清理過期事件
- 其他定時任務
"""
import logging
from typing import Optional
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# 全域排程器實例
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """取得排程器實例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def process_pending_reminders_job():
    """處理待發送提醒的排程任務"""
    from app.db.database import async_session_maker
    from app.services.reminder_service import ReminderService

    logger.info("開始執行提醒處理排程任務")

    try:
        async with async_session_maker() as db:
            service = ReminderService(db)
            stats = await service.process_pending_reminders()
            logger.info(f"提醒處理完成: 總數={stats['total']}, 成功={stats['sent']}, 失敗={stats['failed']}")
    except Exception as e:
        logger.error(f"提醒處理排程任務失敗: {e}", exc_info=True)


async def cleanup_expired_events_job():
    """清理過期事件的排程任務"""
    from app.db.database import async_session_maker
    from app.services.document_calendar_service import DocumentCalendarService
    from datetime import datetime, timedelta

    logger.info("開始執行過期事件清理排程任務")

    try:
        async with async_session_maker() as db:
            # 清理 30 天前的已完成事件
            cutoff_date = datetime.now() - timedelta(days=30)
            # 此處可添加清理邏輯，目前僅記錄日誌
            logger.info(f"過期事件清理任務執行完成 (截止日期: {cutoff_date})")
    except Exception as e:
        logger.error(f"過期事件清理排程任務失敗: {e}", exc_info=True)


def setup_scheduler(
    reminder_interval_minutes: int = 5,
    cleanup_hour: int = 2,
    cleanup_minute: int = 0
) -> AsyncIOScheduler:
    """
    設定排程器

    Args:
        reminder_interval_minutes: 提醒處理間隔（分鐘）
        cleanup_hour: 清理任務執行小時
        cleanup_minute: 清理任務執行分鐘

    Returns:
        設定完成的排程器
    """
    scheduler = get_scheduler()

    # 移除現有任務（避免重複添加）
    existing_jobs = scheduler.get_jobs()
    for job in existing_jobs:
        scheduler.remove_job(job.id)

    # 添加提醒處理任務 - 每 N 分鐘執行一次
    scheduler.add_job(
        process_pending_reminders_job,
        trigger=IntervalTrigger(minutes=reminder_interval_minutes),
        id='process_reminders',
        name='處理待發送提醒',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info(f"已添加提醒處理任務: 每 {reminder_interval_minutes} 分鐘執行")

    # 添加清理任務 - 每日凌晨執行
    scheduler.add_job(
        cleanup_expired_events_job,
        trigger=CronTrigger(hour=cleanup_hour, minute=cleanup_minute),
        id='cleanup_events',
        name='清理過期事件',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info(f"已添加清理任務: 每日 {cleanup_hour:02d}:{cleanup_minute:02d} 執行")

    return scheduler


def start_scheduler():
    """啟動排程器"""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("排程器已啟動")
    else:
        logger.info("排程器已在運行中")


def stop_scheduler():
    """停止排程器"""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("排程器已停止")


def get_scheduler_status() -> dict:
    """取得排程器狀態"""
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    return {
        'running': scheduler.running,
        'jobs': [
            {
                'id': job.id,
                'name': job.name,
                'next_run_time': str(job.next_run_time) if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            for job in jobs
        ]
    }


@asynccontextmanager
async def scheduler_lifespan():
    """
    排程器生命週期管理（用於 FastAPI lifespan）

    Usage:
        app = FastAPI(lifespan=scheduler_lifespan)
    """
    setup_scheduler()
    start_scheduler()
    logger.info("排程器已隨應用程式啟動")
    try:
        yield
    finally:
        stop_scheduler()
        logger.info("排程器已隨應用程式關閉")
