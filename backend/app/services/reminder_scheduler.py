"""
提醒排程服務
自動處理定時提醒任務的背景服務
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from app.db.database import AsyncSessionLocal
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

class ReminderScheduler:
    """提醒排程器"""

    def __init__(self, check_interval: int = 300):  # 預設每5分鐘檢查一次
        self.check_interval = check_interval
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """啟動排程器"""
        if self.is_running:
            logger.warning("提醒排程器已經在運行中")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"提醒排程器已啟動，檢查間隔: {self.check_interval} 秒")

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

        logger.info("提醒排程器已停止")

    async def _run_scheduler(self):
        """運行排程器主循環"""
        logger.info("提醒排程器開始運行")

        while self.is_running:
            try:
                # 執行提醒處理
                await self._process_reminders()

                # 等待下次檢查
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info("提醒排程器收到取消信號")
                break
            except Exception as e:
                logger.error(f"提醒排程器運行錯誤: {e}", exc_info=True)
                # 等待一段時間後重試
                await asyncio.sleep(min(self.check_interval, 60))

        logger.info("提醒排程器停止運行")

    async def _process_reminders(self):
        """處理待發送的提醒"""
        db = None
        try:
            # 直接創建 session（不使用依賴注入生成器）
            db = AsyncSessionLocal()
            service = ReminderService(db)
            stats = await service.process_pending_reminders()

            if stats["total"] > 0:
                logger.info(
                    f"提醒處理完成 - 總計: {stats['total']}, "
                    f"成功: {stats['sent']}, "
                    f"失敗: {stats['failed']}, "
                    f"重試: {stats['retries']}"
                )

            await db.commit()

        except Exception as e:
            logger.error(f"處理提醒時發生錯誤: {e}", exc_info=True)
            if db:
                await db.rollback()
        finally:
            if db:
                await db.close()

    async def process_once(self):
        """手動執行一次提醒處理（用於測試或手動觸發）"""
        logger.info("手動執行提醒處理")
        await self._process_reminders()

    def get_status(self) -> dict:
        """獲取排程器狀態"""
        return {
            "is_running": self.is_running,
            "check_interval": self.check_interval,
            "task_active": self._task is not None and not self._task.done() if self._task else False
        }

# 全域排程器實例
_reminder_scheduler: Optional[ReminderScheduler] = None

def get_reminder_scheduler() -> ReminderScheduler:
    """獲取全域提醒排程器實例"""
    global _reminder_scheduler
    if _reminder_scheduler is None:
        _reminder_scheduler = ReminderScheduler()
    return _reminder_scheduler

@asynccontextmanager
async def reminder_scheduler_lifespan():
    """提醒排程器生命週期管理器（用於 FastAPI lifespan）"""
    scheduler = get_reminder_scheduler()
    try:
        await scheduler.start()
        yield scheduler
    finally:
        await scheduler.stop()

async def start_reminder_scheduler():
    """啟動提醒排程器（用於應用程式啟動時調用）"""
    scheduler = get_reminder_scheduler()
    await scheduler.start()

async def stop_reminder_scheduler():
    """停止提醒排程器（用於應用程式關閉時調用）"""
    scheduler = get_reminder_scheduler()
    await scheduler.stop()

# 排程器控制 API（用於運維）
class ReminderSchedulerController:
    """提醒排程器控制器"""

    @staticmethod
    async def start_scheduler():
        """啟動排程器"""
        scheduler = get_reminder_scheduler()
        await scheduler.start()
        return scheduler.get_status()

    @staticmethod
    async def stop_scheduler():
        """停止排程器"""
        scheduler = get_reminder_scheduler()
        await scheduler.stop()
        return scheduler.get_status()

    @staticmethod
    async def restart_scheduler():
        """重啟排程器"""
        scheduler = get_reminder_scheduler()
        await scheduler.stop()
        await asyncio.sleep(1)  # 短暫等待
        await scheduler.start()
        return scheduler.get_status()

    @staticmethod
    def get_scheduler_status():
        """獲取排程器狀態"""
        scheduler = get_reminder_scheduler()
        return scheduler.get_status()

    @staticmethod
    async def trigger_manual_process():
        """手動觸發一次提醒處理"""
        scheduler = get_reminder_scheduler()
        await scheduler.process_once()
        return {"message": "手動提醒處理已完成"}

    @staticmethod
    async def update_check_interval(new_interval: int):
        """更新檢查間隔"""
        if new_interval < 60:  # 最小間隔60秒
            raise ValueError("檢查間隔不能少於60秒")

        scheduler = get_reminder_scheduler()
        was_running = scheduler.is_running

        # 如果正在運行，需要重啟以應用新設定
        if was_running:
            await scheduler.stop()

        scheduler.check_interval = new_interval

        if was_running:
            await scheduler.start()

        return {
            "message": f"檢查間隔已更新為 {new_interval} 秒",
            "status": scheduler.get_status()
        }