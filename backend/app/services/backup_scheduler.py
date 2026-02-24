"""
資料庫備份排程器
提供每日自動備份與異地自動同步功能

使用 asyncio 實現，與其他排程器保持一致

@version 2.0.0
@date 2026-02-24

變更記錄:
- v2.0.0: 備份失敗通知、自動異地同步排程
- v1.2.0: 從備份日誌檔案載入統計數據，避免重啟後歸零
"""

import asyncio
import json
import logging
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Optional

from app.services.backup import backup_service

logger = logging.getLogger(__name__)


async def _notify_backup_event(
    title: str,
    message: str,
    severity: str = "error",
    data: Optional[dict] = None,
) -> None:
    """發送備份相關系統通知（使用獨立 session，不影響備份流程）"""
    try:
        from app.db.database import AsyncSessionLocal
        from app.extended.models import SystemNotification

        async with AsyncSessionLocal() as db:
            try:
                notification = SystemNotification(
                    user_id=None,  # 廣播給所有管理員
                    title=title,
                    message=message,
                    notification_type="system",
                    is_read=False,
                    data={"severity": severity, "source_table": "backup", **(data or {})},
                )
                db.add(notification)
                await db.commit()
                logger.info(f"[BACKUP-NOTIFY] {severity.upper()}: {title}")
            except Exception as db_err:
                await db.rollback()
                logger.warning(f"[BACKUP-NOTIFY] 通知建立失敗: {db_err}")
    except Exception as e:
        # 通知失敗不應阻斷備份流程
        logger.warning(f"[BACKUP-NOTIFY] Session 建立失敗: {e}")


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
        self._sync_task: Optional[asyncio.Task] = None
        self._last_backup_time: Optional[datetime] = None
        self._consecutive_failures: int = 0
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

                # 計算尾部連續失敗次數（從最近往回數）
                consecutive = 0
                for log in reversed(create_logs):
                    if log.get('status') == 'success':
                        break
                    consecutive += 1
                self._consecutive_failures = consecutive

                logger.info(f"從日誌載入備份統計: {stats['total_backups']} 次 "
                           f"(成功: {stats['successful_backups']}, 失敗: {stats['failed_backups']}, "
                           f"連續失敗: {consecutive})")
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
                self._consecutive_failures = 0
                db_info = result.get("database_backup", {})
                att_info = result.get("attachments_backup", {})

                logger.info(
                    f"✅ 每日備份完成 - "
                    f"資料庫: {db_info.get('filename', 'N/A')} ({db_info.get('size_kb', 0)} KB), "
                    f"附件: {att_info.get('dirname', 'N/A')} ({att_info.get('file_count', 0)} 檔案)"
                )
            else:
                self._backup_stats['failed_backups'] += 1
                self._consecutive_failures += 1
                errors = result.get("errors", [])
                logger.error(f"❌ 每日備份失敗: {errors}")
                await self._handle_backup_failure("; ".join(errors))

        except Exception as e:
            self._backup_stats['failed_backups'] += 1
            self._consecutive_failures += 1
            self._backup_stats['last_backup_result'] = {"success": False, "error": str(e)}
            logger.exception(f"❌ 每日備份發生例外: {e}")
            await self._handle_backup_failure(str(e))

    async def _handle_backup_failure(self, error_msg: str) -> None:
        """處理備份失敗：根據連續失敗次數發送不同等級通知"""
        n = self._consecutive_failures
        if n == 1:
            # 首次失敗：warning 級別
            await _notify_backup_event(
                title="每日自動備份失敗",
                message=f"備份於 {datetime.now().strftime('%Y-%m-%d %H:%M')} 失敗: {error_msg[:200]}",
                severity="warning",
                data={"consecutive_failures": n},
            )
        elif n >= 2:
            # 連續失敗：critical 級別
            await _notify_backup_event(
                title=f"備份連續失敗 {n} 次 — 需立即處理",
                message=(
                    f"自動備份已連續失敗 {n} 次，最近錯誤: {error_msg[:200]}。"
                    f"請檢查 Docker 服務與磁碟空間。"
                ),
                severity="critical",
                data={"consecutive_failures": n},
            )

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

    # =========================================================================
    # 異地自動同步排程
    # =========================================================================

    async def _remote_sync_loop(self) -> None:
        """異地同步排程迴圈：根據 remote_config.sync_interval_hours 自動同步"""
        # 啟動後等待 5 分鐘再開始（讓備份服務完全初始化）
        await asyncio.sleep(300)

        while self.is_running:
            try:
                config = backup_service._remote_config
                sync_enabled = config.get("sync_enabled", False)
                remote_path = config.get("remote_path")
                interval_hours = config.get("sync_interval_hours", 24)

                if not sync_enabled or not remote_path:
                    # 未啟用或未設定路徑，每 10 分鐘重新檢查
                    await asyncio.sleep(600)
                    continue

                # 計算距離上次同步的時間
                last_sync = config.get("last_sync_time")
                need_sync = True
                if last_sync:
                    try:
                        last_sync_dt = datetime.fromisoformat(last_sync)
                        elapsed_hours = (datetime.now() - last_sync_dt).total_seconds() / 3600
                        if elapsed_hours < interval_hours:
                            # 尚未到達同步間隔，等待剩餘時間
                            wait_seconds = (interval_hours - elapsed_hours) * 3600
                            logger.debug(
                                f"異地同步尚未到期，{elapsed_hours:.1f}/{interval_hours}h，"
                                f"等待 {wait_seconds / 3600:.1f}h"
                            )
                            await asyncio.sleep(min(wait_seconds, 3600))  # 最多等 1 小時再檢查
                            need_sync = False
                    except (ValueError, TypeError):
                        pass  # 時間解析失敗，立即同步

                if need_sync and self.is_running:
                    logger.info("開始自動異地備份同步...")
                    result = await backup_service.sync_to_remote()
                    if result.get("success"):
                        logger.info(
                            f"✅ 異地同步完成: {result.get('synced_files', 0)} 檔案, "
                            f"{result.get('total_size_kb', 0)} KB"
                        )
                    else:
                        error = result.get("error", "未知錯誤")
                        logger.error(f"❌ 異地同步失敗: {error}")
                        await _notify_backup_event(
                            title="異地備份同步失敗",
                            message=f"自動同步到 {remote_path} 失敗: {error[:200]}",
                            severity="warning",
                            data={"remote_path": str(remote_path)},
                        )

                    # 同步完成後等待至少 1 小時再檢查
                    await asyncio.sleep(3600)

            except asyncio.CancelledError:
                logger.info("異地同步排程迴圈被取消")
                break
            except Exception as e:
                logger.exception(f"異地同步排程發生錯誤: {e}")
                await asyncio.sleep(600)  # 錯誤後 10 分鐘重試

    # =========================================================================
    # 啟動 / 停止 / 狀態
    # =========================================================================

    async def start(self) -> None:
        """啟動排程器（含備份排程 + 異地同步排程）"""
        if self.is_running:
            logger.warning("備份排程器已經在運行中")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        self._sync_task = asyncio.create_task(self._remote_sync_loop())
        next_backup = self._get_next_backup_time()
        logger.info(
            f"✅ 備份排程器已啟動 "
            f"(每日 {self.backup_hour:02d}:{self.backup_minute:02d} 執行，"
            f"下次: {next_backup.strftime('%Y-%m-%d %H:%M:%S')}，"
            f"異地同步排程已啟動)"
        )

    async def stop(self) -> None:
        """停止排程器"""
        if not self.is_running:
            return

        self.is_running = False
        for task in [self._task, self._sync_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._task = None
        self._sync_task = None

        logger.info("✅ 備份排程器已停止")

    def get_status(self) -> dict:
        """取得排程器狀態"""
        # 異地同步狀態
        remote_config = backup_service._remote_config
        remote_sync_info = {
            "enabled": remote_config.get("sync_enabled", False),
            "interval_hours": remote_config.get("sync_interval_hours", 24),
            "last_sync": remote_config.get("last_sync_time"),
            "status": remote_config.get("sync_status", "idle"),
        }

        return {
            "running": self.is_running,
            "backup_time": f"{self.backup_hour:02d}:{self.backup_minute:02d}",
            "next_backup": self._get_next_backup_time().isoformat() if self.is_running else None,
            "last_backup": self._last_backup_time.isoformat() if self._last_backup_time else None,
            "consecutive_failures": self._consecutive_failures,
            "remote_sync": remote_sync_info,
            "stats": self._backup_stats,
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


