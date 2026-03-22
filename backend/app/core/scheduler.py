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


async def einvoice_sync_job():
    """電子發票自動同步排程任務 — 每晚從財政部下載公司統編發票"""
    from app.db.database import async_session_maker
    from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService

    logger.info("開始執行電子發票自動同步排程任務")

    try:
        async with async_session_maker() as db:
            service = EInvoiceSyncService(db)
            stats = await service.sync_invoices()
            logger.info(
                f"電子發票同步完成: 取得={stats.get('total_fetched', 0)}, "
                f"新增={stats.get('new_imported', 0)}, "
                f"重複={stats.get('skipped_duplicate', 0)}"
            )
    except Exception as e:
        logger.error(f"電子發票同步排程任務失敗: {e}", exc_info=True)


async def proactive_trigger_scan_job():
    """
    NemoClaw 夜間吹哨者 — 掃描 PM/ERP 預算超支、逾期請款、待核銷發票等警報。

    掃描結果：
    1. 持久化至 SystemNotification (DB)
    2. 推播至 LINE (若已設定)
    """
    from app.db.database import async_session_maker
    from app.services.ai.proactive_triggers import ProactiveTriggerService
    from app.services.ai.proactive_triggers_erp import ERPTriggerScanner
    from app.services.notification_helpers import _safe_create_notification

    logger.info("開始執行 NemoClaw 夜間吹哨者掃描")

    try:
        async with async_session_maker() as db:
            # 掃描基礎警報 (公文截止日/資料品質)
            base_service = ProactiveTriggerService(db)
            base_alerts = await base_service.scan_all()

            # 掃描 ERP 警報 (預算/請款/發票/廠商付款)
            erp_scanner = ERPTriggerScanner(db)
            erp_alerts = await erp_scanner.scan_all()

            all_alerts = base_alerts + erp_alerts

            # 篩選 warning 以上持久化至 DB
            severity_order = {"critical": 3, "warning": 2, "info": 1}
            actionable = [
                a for a in all_alerts
                if severity_order.get(a.severity, 0) >= 2
            ]

            persisted = 0
            for alert in actionable:
                ok = await _safe_create_notification(
                    notification_type="proactive_alert",
                    severity=alert.severity,
                    title=alert.title,
                    message=alert.message,
                    source_table=alert.entity_type,
                    source_id=alert.entity_id,
                    changes=alert.metadata,
                )
                if ok:
                    persisted += 1

            logger.info(
                f"NemoClaw 吹哨者完成: "
                f"掃描={len(all_alerts)}, "
                f"warning+={len(actionable)}, "
                f"已通知={persisted}"
            )

            # LINE 推播 (嘗試性，失敗不影響主流程)
            try:
                from app.services.line_push_scheduler import LinePushScheduler
                push_scheduler = LinePushScheduler(db)
                push_result = await push_scheduler.scan_and_push(min_severity="warning")
                if push_result.get("sent", 0) > 0:
                    logger.info(f"LINE 推播完成: {push_result}")
            except Exception as line_err:
                logger.debug(f"LINE 推播跳過: {line_err}")

    except Exception as e:
        logger.error(f"NemoClaw 夜間吹哨者失敗: {e}", exc_info=True)


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

    # 添加電子發票同步任務 - 每日凌晨 01:00 執行
    import os
    if os.getenv("MOF_APP_ID"):
        scheduler.add_job(
            einvoice_sync_job,
            trigger=CronTrigger(hour=1, minute=0),
            id='einvoice_sync',
            name='電子發票自動同步 (財政部)',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info("已添加電子發票同步任務: 每日 01:00 執行")
    else:
        logger.info("電子發票同步未啟用 (MOF_APP_ID 未設定)")

    # 添加 NemoClaw 夜間吹哨者 — 每日 00:30 掃描預算/逾期/待核銷
    scheduler.add_job(
        proactive_trigger_scan_job,
        trigger=CronTrigger(hour=0, minute=30),
        id='proactive_trigger_scan',
        name='NemoClaw 夜間吹哨者 (預算/逾期/待核銷)',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    logger.info("已添加 NemoClaw 夜間吹哨者: 每日 00:30 執行")

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
