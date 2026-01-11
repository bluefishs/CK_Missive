"""
資料庫備份排程器
提供每日自動備份功能

@version 1.0.0
@date 2026-01-11
"""

import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.backup_service import backup_service

logger = logging.getLogger(__name__)

# 排程器實例
backup_scheduler: Optional[AsyncIOScheduler] = None


async def perform_daily_backup():
    """
    執行每日備份任務

    此函數由排程器自動觸發
    """
    logger.info(f"[{datetime.now()}] 開始執行每日自動備份...")

    try:
        result = await backup_service.create_backup(
            include_database=True,
            include_attachments=True,
            retention_days=7  # 保留 7 天
        )

        if result.get("success"):
            db_info = result.get("database_backup", {})
            att_info = result.get("attachments_backup", {})

            logger.info(
                f"✅ 每日備份完成 - "
                f"資料庫: {db_info.get('filename', 'N/A')} ({db_info.get('size_kb', 0)} KB), "
                f"附件: {att_info.get('dirname', 'N/A')} ({att_info.get('file_count', 0)} 檔案)"
            )
        else:
            errors = result.get("errors", [])
            logger.error(f"❌ 每日備份失敗: {errors}")

    except Exception as e:
        logger.exception(f"❌ 每日備份發生例外: {e}")


async def start_backup_scheduler():
    """
    啟動備份排程器

    預設排程: 每日凌晨 2:00 執行備份
    """
    global backup_scheduler

    if backup_scheduler is not None and backup_scheduler.running:
        logger.warning("備份排程器已在運行中")
        return

    backup_scheduler = AsyncIOScheduler()

    # 每日凌晨 2:00 執行
    backup_scheduler.add_job(
        perform_daily_backup,
        CronTrigger(hour=2, minute=0),
        id="daily_backup",
        name="每日資料庫備份",
        replace_existing=True
    )

    backup_scheduler.start()
    logger.info("✅ 備份排程器已啟動 (每日 02:00 執行)")


async def stop_backup_scheduler():
    """停止備份排程器"""
    global backup_scheduler

    if backup_scheduler is not None:
        backup_scheduler.shutdown(wait=False)
        backup_scheduler = None
        logger.info("✅ 備份排程器已停止")


def get_backup_scheduler_status() -> dict:
    """
    取得備份排程器狀態

    Returns:
        排程器狀態資訊
    """
    if backup_scheduler is None:
        return {"running": False, "next_run": None}

    job = backup_scheduler.get_job("daily_backup")
    next_run = None

    if job and job.next_run_time:
        next_run = job.next_run_time.isoformat()

    return {
        "running": backup_scheduler.running,
        "next_run": next_run,
        "job_count": len(backup_scheduler.get_jobs())
    }
