"""
資料庫備份排程器
提供每日自動備份功能

使用 asyncio 實現，與其他排程器保持一致

@version 1.2.0
@date 2026-02-02

變更記錄:
- v1.2.0: 從備份日誌檔案載入統計數據，避免重啟後歸零
"""

import asyncio
import json
import logging
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Optional

from app.services.backup_service import backup_service

logger = logging.getLogger(__name__)


class BackupScheduler:
    """備份排程器"""

    def __init__(self, backup_hour: int = 2, backup_minute: int = 0) -> None:
        """
        初始化備份排程器

        Args:
            backup_hour: 備份執行小時 (0-23)，預設 2 點
            backup_minute: 備份執行分鐘 (0-59)，預設 0 分
        """
        self.backup_hour: int = backup_hour
        self.backup_minute: int = backup_minute
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._last_backup_time: Optional[datetime] = None
        self._backup_stats: dict = self._load_stats_from_logs()

    def _load_stats_from_logs(self) -> dict:
        """
        從備份日誌檔案載入統計數據

        讀取 backup_operations.json，計算成功/失敗次數，
        避免重啟後統計數據歸零。
        """
        stats = {
            'total_backups': 0,
            'successful_backups': 0,
            'failed_backups': 0,
            'last_backup_result': None
        }

        try:
            # 使用與 backup_service 相同的日誌路徑
            log_file = backup_service.backup_log_file
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)

                # 統計 'create' 操作的成功/失敗次數
                for log in logs:
                    if log.get('action') == 'create':
                        stats['total_backups'] += 1
                        if log.get('status') == 'success':
                            stats['successful_backups'] += 1
                        else:
                            stats['failed_backups'] += 1

                # 取得最近的備份結果
                create_logs = [l for l in logs if l.get('action') == 'create']
                if create_logs:
                    last_log = create_logs[-1]
                    stats['last_backup_result'] = {
                        'success': last_log.get('status') == 'success',
                        'timestamp': last_log.get('timestamp'),
                        'details': last_log.get('details')
                    }

                logger.info(f"從日誌載入備份統計: {stats['total_backups']} 次 "
                           f"(成功: {stats['successful_backups']}, 失敗: {stats['failed_backups']})")
        except Exception as e:
            logger.warning(f"載入備份統計失敗: {e}")

        return stats

    def _get_next_backup_time(self) -> datetime:
        """計算下次備份時間"""
        now = datetime.now()
        backup_time = now.replace(
            hour=self.backup_hour,
            minute=self.backup_minute,
            second=0,
            microsecond=0
        )

        # 如果今天的備份時間已過，則設定為明天
        if backup_time <= now:
            backup_time += timedelta(days=1)

        return backup_time

    def _get_seconds_until_backup(self) -> float:
        """
        計算距離下次備份的秒數

        Returns:
            距離下次備份的秒數
        """
        next_backup = self._get_next_backup_time()
        delta = next_backup - datetime.now()
        return max(delta.total_seconds(), 0)

    async def _perform_backup(self) -> None:
        """執行備份任務"""
        logger.info(f"[{datetime.now()}] 開始執行每日自動備份...")
        self._backup_stats['total_backups'] += 1

        try:
            result = await backup_service.create_backup(
                include_database=True,
                include_attachments=True,
                retention_days=7  # 保留 7 天
            )

            self._last_backup_time = datetime.now()
            self._backup_stats['last_backup_result'] = result

            if result.get("success"):
                self._backup_stats['successful_backups'] += 1
                db_info = result.get("database_backup", {})
                att_info = result.get("attachments_backup", {})

                logger.info(
                    f"✅ 每日備份完成 - "
                    f"資料庫: {db_info.get('filename', 'N/A')} ({db_info.get('size_kb', 0)} KB), "
                    f"附件: {att_info.get('dirname', 'N/A')} ({att_info.get('file_count', 0)} 檔案)"
                )
            else:
                self._backup_stats['failed_backups'] += 1
                errors = result.get("errors", [])
                logger.error(f"❌ 每日備份失敗: {errors}")

        except Exception as e:
            self._backup_stats['failed_backups'] += 1
            self._backup_stats['last_backup_result'] = {"success": False, "error": str(e)}
            logger.exception(f"❌ 每日備份發生例外: {e}")

    async def _scheduler_loop(self) -> None:
        """排程器主迴圈"""
        while self.is_running:
            try:
                # 計算等待時間
                wait_seconds = self._get_seconds_until_backup()
                next_backup = self._get_next_backup_time()

                logger.info(
                    f"📅 下次備份時間: {next_backup.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(約 {wait_seconds / 3600:.1f} 小時後)"
                )

                # 等待到備份時間
                await asyncio.sleep(wait_seconds)

                # 執行備份
                if self.is_running:
                    await self._perform_backup()

            except asyncio.CancelledError:
                logger.info("備份排程器迴圈被取消")
                break
            except Exception as e:
                logger.exception(f"備份排程器迴圈發生錯誤: {e}")
                # 發生錯誤時等待 5 分鐘後重試
                await asyncio.sleep(300)

    async def start(self) -> None:
        """啟動排程器"""
        if self.is_running:
            logger.warning("備份排程器已經在運行中")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        next_backup = self._get_next_backup_time()
        logger.info(
            f"✅ 備份排程器已啟動 "
            f"(每日 {self.backup_hour:02d}:{self.backup_minute:02d} 執行，"
            f"下次: {next_backup.strftime('%Y-%m-%d %H:%M:%S')})"
        )

    async def stop(self) -> None:
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

        logger.info("✅ 備份排程器已停止")

    def get_status(self) -> dict:
        """取得排程器狀態"""
        return {
            "running": self.is_running,
            "backup_time": f"{self.backup_hour:02d}:{self.backup_minute:02d}",
            "next_backup": self._get_next_backup_time().isoformat() if self.is_running else None,
            "last_backup": self._last_backup_time.isoformat() if self._last_backup_time else None,
            "stats": self._backup_stats
        }


# 全域排程器實例
_backup_scheduler: Optional[BackupScheduler] = None


async def start_backup_scheduler() -> None:
    """啟動備份排程器"""
    global _backup_scheduler
    if _backup_scheduler is None:
        _backup_scheduler = BackupScheduler(backup_hour=2, backup_minute=0)
    await _backup_scheduler.start()


async def stop_backup_scheduler() -> None:
    """停止備份排程器"""
    global _backup_scheduler
    if _backup_scheduler is not None:
        await _backup_scheduler.stop()


def get_backup_scheduler() -> Optional[BackupScheduler]:
    """取得備份排程器實例"""
    return _backup_scheduler


def get_backup_scheduler_status() -> dict:
    """取得備份排程器狀態"""
    if _backup_scheduler is None:
        return {"running": False, "next_backup": None}
    return _backup_scheduler.get_status()


