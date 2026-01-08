"""
Google Calendar 同步排程器
自動將本地事件同步至 Google Calendar
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from app.db.database import get_async_db
from app.services.document_calendar_service import calendar_service

logger = logging.getLogger(__name__)


class GoogleSyncScheduler:
    """Google Calendar 自動同步排程器"""

    def __init__(self, sync_interval: int = 600):  # 預設每 10 分鐘同步一次
        self.sync_interval = sync_interval
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self._last_sync_time: Optional[datetime] = None
        self._sync_stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_sync_result': None
        }

    async def start(self):
        """啟動排程器"""
        if self.is_running:
            logger.warning("Google Calendar 同步排程器已在運行中")
            return

        if not calendar_service.is_ready():
            logger.warning("Google Calendar 服務未就緒，排程器無法啟動")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Google Calendar 同步排程器已啟動，同步間隔: {self.sync_interval} 秒")

    async def stop(self):
        """停止排程器"""
        if not self.is_running:
            return

        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Google Calendar 同步排程器已停止")

    async def _run_scheduler(self):
        """執行排程器主循環"""
        logger.info("Google Calendar 同步排程器開始運行")

        while self.is_running:
            try:
                # 執行同步
                await self._process_sync()

                # 等待下次同步
                await asyncio.sleep(self.sync_interval)

            except asyncio.CancelledError:
                logger.info("Google Calendar 同步排程器收到取消信號")
                break
            except Exception as e:
                logger.error(f"Google Calendar 同步排程器運行錯誤: {e}", exc_info=True)
                # 錯誤後等待較短時間再重試
                await asyncio.sleep(min(self.sync_interval, 60))

        logger.info("Google Calendar 同步排程器停止運行")

    async def _process_sync(self):
        """處理待同步的事件"""
        try:
            async for db in get_async_db():
                # 取得待同步事件
                pending_events = await calendar_service.get_pending_sync_events(db, limit=20)

                if not pending_events:
                    logger.debug("沒有待同步的 Google Calendar 事件")
                    return

                logger.info(f"開始同步 {len(pending_events)} 個事件至 Google Calendar")

                synced_count = 0
                failed_count = 0

                for event in pending_events:
                    result = await calendar_service.sync_event_to_google(db, event)
                    if result['success']:
                        synced_count += 1
                    else:
                        failed_count += 1

                # 更新統計
                self._last_sync_time = datetime.now()
                self._sync_stats['total_syncs'] += 1
                self._sync_stats['successful_syncs'] += synced_count
                self._sync_stats['failed_syncs'] += failed_count
                self._sync_stats['last_sync_result'] = {
                    'time': self._last_sync_time.isoformat(),
                    'synced': synced_count,
                    'failed': failed_count
                }

                if synced_count > 0 or failed_count > 0:
                    logger.info(
                        f"Google Calendar 同步完成 - 成功: {synced_count}, 失敗: {failed_count}"
                    )

        except Exception as e:
            logger.error(f"處理 Google Calendar 同步時發生錯誤: {e}", exc_info=True)

    async def process_once(self):
        """手動執行一次同步（用於測試或手動觸發）"""
        logger.info("手動執行 Google Calendar 同步")
        await self._process_sync()

    def get_status(self) -> dict:
        """獲取排程器狀態"""
        return {
            "is_running": self.is_running,
            "sync_interval": self.sync_interval,
            "task_active": self._task is not None and not self._task.done() if self._task else False,
            "google_service_ready": calendar_service.is_ready(),
            "calendar_id": calendar_service.calendar_id if calendar_service.is_ready() else None,
            "last_sync_time": self._last_sync_time.isoformat() if self._last_sync_time else None,
            "stats": self._sync_stats
        }


# 全域排程器實例
_google_sync_scheduler: Optional[GoogleSyncScheduler] = None


def get_google_sync_scheduler() -> GoogleSyncScheduler:
    """獲取全域 Google Calendar 同步排程器實例"""
    global _google_sync_scheduler
    if _google_sync_scheduler is None:
        _google_sync_scheduler = GoogleSyncScheduler()
    return _google_sync_scheduler


@asynccontextmanager
async def google_sync_scheduler_lifespan():
    """Google Calendar 同步排程器生命週期管理器（用於 FastAPI lifespan）"""
    scheduler = get_google_sync_scheduler()
    try:
        await scheduler.start()
        yield scheduler
    finally:
        await scheduler.stop()


async def start_google_sync_scheduler():
    """啟動 Google Calendar 同步排程器（用於應用程式啟動時調用）"""
    scheduler = get_google_sync_scheduler()
    await scheduler.start()


async def stop_google_sync_scheduler():
    """停止 Google Calendar 同步排程器（用於應用程式關閉時調用）"""
    scheduler = get_google_sync_scheduler()
    await scheduler.stop()


# 排程器控制 API
class GoogleSyncSchedulerController:
    """Google Calendar 同步排程器控制器"""

    @staticmethod
    async def start_scheduler():
        """啟動排程器"""
        scheduler = get_google_sync_scheduler()
        await scheduler.start()
        return scheduler.get_status()

    @staticmethod
    async def stop_scheduler():
        """停止排程器"""
        scheduler = get_google_sync_scheduler()
        await scheduler.stop()
        return scheduler.get_status()

    @staticmethod
    async def restart_scheduler():
        """重啟排程器"""
        scheduler = get_google_sync_scheduler()
        await scheduler.stop()
        await asyncio.sleep(1)
        await scheduler.start()
        return scheduler.get_status()

    @staticmethod
    def get_scheduler_status():
        """獲取排程器狀態"""
        scheduler = get_google_sync_scheduler()
        return scheduler.get_status()

    @staticmethod
    async def trigger_manual_sync():
        """手動觸發一次同步"""
        scheduler = get_google_sync_scheduler()
        await scheduler.process_once()
        return {"message": "手動 Google Calendar 同步已完成", "status": scheduler.get_status()}

    @staticmethod
    async def update_sync_interval(new_interval: int):
        """更新同步間隔"""
        if new_interval < 60:
            raise ValueError("同步間隔不能少於 60 秒")

        scheduler = get_google_sync_scheduler()
        was_running = scheduler.is_running

        if was_running:
            await scheduler.stop()

        scheduler.sync_interval = new_interval

        if was_running:
            await scheduler.start()

        return {
            "message": f"同步間隔已更新為 {new_interval} 秒",
            "status": scheduler.get_status()
        }
