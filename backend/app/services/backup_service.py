"""
資料庫備份服務
提供資料庫與附件的備份、還原、列表與管理功能
支援異地備份路徑設定與備份日誌記錄

@version 1.1.0
@date 2026-01-29
"""

import os
import subprocess
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import shutil
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class BackupService:
    """備份服務類別"""

    def __init__(self) -> None:
        """初始化備份服務"""
        # 專案根目錄 - 容器內使用 /app
        self.project_root: Path = Path("/app")

        # 備份目錄 - 使用容器內路徑
        self.backup_dir = Path("/app/backups/database")
        self.attachment_backup_dir = Path("/app/backups/attachments")
        self.uploads_dir = Path("/app/uploads")
        self.log_dir = Path("/app/logs/backup")

        # 備份腳本路徑
        self.backup_script = self.project_root / "scripts" / "backup" / "db_backup.ps1"
        self.restore_script = (
            self.project_root / "scripts" / "backup" / "db_restore.ps1"
        )

        # 資料庫連線設定 - 從 settings 讀取，不再硬編碼
        self.db_user = settings.POSTGRES_USER
        self.db_password = settings.POSTGRES_PASSWORD
        self.db_name = settings.POSTGRES_DB
        self.container_name = "ck_missive_postgres_dev"

        # 從環境變數讀取設定 (覆蓋 settings 的值)
        self._load_env_config()

        # 異地備份設定
        self.remote_config_file = self.project_root / "config" / "remote_backup.json"
        self._remote_config: Dict[str, Any] = self._load_remote_config()

        # 備份日誌檔案
        self.backup_log_file = self.log_dir / "backup_operations.json"
        self._backup_logs: List[Dict[str, Any]] = self._load_backup_logs()

        # 確保目錄存在
        self._ensure_directories()

    def _load_env_config(self) -> None:
        """從環境變數載入設定"""
        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("POSTGRES_USER="):
                        self.db_user = line.split("=", 1)[1]
                    elif line.startswith("POSTGRES_PASSWORD="):
                        self.db_password = line.split("=", 1)[1]
                    elif line.startswith("POSTGRES_DB="):
                        self.db_name = line.split("=", 1)[1]

    def _ensure_directories(self) -> None:
        """確保備份目錄存在"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.attachment_backup_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_running_container(self) -> Optional[str]:
        """取得正在執行的 PostgreSQL 容器名稱"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return self.container_name

    async def create_backup(
        self,
        include_database: bool = True,
        include_attachments: bool = True,
        retention_days: int = 7,
    ) -> Dict[str, Any]:
        """
        建立備份

        Args:
            include_database: 是否包含資料庫
            include_attachments: 是否包含附件
            retention_days: 保留天數

        Returns:
            備份結果資訊
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = {
            "success": True,
            "timestamp": timestamp,
            "database_backup": None,
            "attachments_backup": None,
            "errors": [],
        }

        # 資料庫備份
        if include_database:
            db_result = await self._backup_database(timestamp)
            result["database_backup"] = db_result
            if not db_result.get("success"):
                result["errors"].append(db_result.get("error"))

        # 附件備份
        if include_attachments:
            att_result = await self._backup_attachments(timestamp)
            result["attachments_backup"] = att_result
            if not att_result.get("success"):
                result["errors"].append(att_result.get("error"))

        # 清理舊備份
        await self._cleanup_old_backups(retention_days)

        result["success"] = len(result["errors"]) == 0
        return result

    async def _backup_database(self, timestamp: str) -> Dict[str, Any]:
        """備份資料庫"""
        container = self._get_running_container()
        backup_file = self.backup_dir / f"ck_missive_backup_{timestamp}.sql"

        try:
            # 使用 pg_dump 備份
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_password

            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    container,
                    "pg_dump",
                    "-U",
                    self.db_user,
                    "-d",
                    self.db_name,
                    "--no-owner",
                    "--no-acl",
                ],
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )

            if result.returncode == 0:
                # 寫入備份檔案
                with open(backup_file, "w", encoding="utf-8") as f:
                    f.write(result.stdout)

                file_size = backup_file.stat().st_size
                return {
                    "success": True,
                    "file": str(backup_file),
                    "filename": backup_file.name,
                    "size_bytes": file_size,
                    "size_kb": round(file_size / 1024, 2),
                }
            else:
                return {"success": False, "error": f"pg_dump failed: {result.stderr}"}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Backup timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _backup_attachments(self, timestamp: str) -> Dict[str, Any]:
        """備份附件"""
        if not self.uploads_dir.exists():
            return {"success": True, "message": "No uploads directory"}

        files = list(self.uploads_dir.rglob("*"))
        file_count = len([f for f in files if f.is_file()])

        if file_count == 0:
            return {"success": True, "message": "No files to backup", "file_count": 0}

        backup_path = self.attachment_backup_dir / f"attachments_backup_{timestamp}"

        try:
            shutil.copytree(self.uploads_dir, backup_path)

            # 計算備份大小
            total_size = sum(
                f.stat().st_size for f in backup_path.rglob("*") if f.is_file()
            )

            return {
                "success": True,
                "path": str(backup_path),
                "dirname": backup_path.name,
                "file_count": file_count,
                "size_bytes": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cleanup_old_backups(self, retention_days: int) -> None:
        """清理過期備份"""
        cutoff = datetime.now() - timedelta(days=retention_days)

        # 清理資料庫備份
        for backup_file in self.backup_dir.glob("ck_missive_backup_*.sql"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff:
                backup_file.unlink()

        # 清理附件備份
        for backup_dir in self.attachment_backup_dir.glob("attachments_backup_*"):
            if backup_dir.is_dir():
                if datetime.fromtimestamp(backup_dir.stat().st_mtime) < cutoff:
                    shutil.rmtree(backup_dir)

    async def list_backups(self) -> Dict[str, Any]:
        """列出所有備份"""
        database_backups = []
        attachment_backups = []

        # 資料庫備份列表
        for backup_file in sorted(
            self.backup_dir.glob("ck_missive_backup_*.sql"), reverse=True
        ):
            stat = backup_file.stat()
            database_backups.append(
                {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "database",
                }
            )

        # 附件備份列表
        for backup_dir in sorted(
            self.attachment_backup_dir.glob("attachments_backup_*"), reverse=True
        ):
            if backup_dir.is_dir():
                stat = backup_dir.stat()
                # 計算目錄大小
                total_size = sum(
                    f.stat().st_size for f in backup_dir.rglob("*") if f.is_file()
                )
                file_count = len(list(backup_dir.rglob("*")))

                attachment_backups.append(
                    {
                        "dirname": backup_dir.name,
                        "path": str(backup_dir),
                        "size_bytes": total_size,
                        "size_mb": round(total_size / (1024 * 1024), 2),
                        "file_count": file_count,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": "attachments",
                    }
                )

        # 統計資訊
        total_db_size = sum(b["size_bytes"] for b in database_backups)
        total_att_size = sum(b["size_bytes"] for b in attachment_backups)

        return {
            "database_backups": database_backups,
            "attachment_backups": attachment_backups,
            "statistics": {
                "database_backup_count": len(database_backups),
                "attachment_backup_count": len(attachment_backups),
                "total_database_size_mb": round(total_db_size / (1024 * 1024), 2),
                "total_attachment_size_mb": round(total_att_size / (1024 * 1024), 2),
                "total_size_mb": round(
                    (total_db_size + total_att_size) / (1024 * 1024), 2
                ),
            },
        }

    async def delete_backup(
        self, backup_name: str, backup_type: str = "database"
    ) -> Dict[str, Any]:
        """刪除指定備份"""
        try:
            if backup_type == "database":
                backup_path = self.backup_dir / backup_name
                if backup_path.exists() and backup_path.is_file():
                    backup_path.unlink()
                    return {"success": True, "message": f"Deleted {backup_name}"}
            elif backup_type == "attachments":
                backup_path = self.attachment_backup_dir / backup_name
                if backup_path.exists() and backup_path.is_dir():
                    shutil.rmtree(backup_path)
                    return {"success": True, "message": f"Deleted {backup_name}"}

            return {"success": False, "error": "Backup not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def restore_database(self, backup_name: str) -> Dict[str, Any]:
        """還原資料庫"""
        backup_file = self.backup_dir / backup_name

        if not backup_file.exists():
            return {"success": False, "error": "Backup file not found"}

        container = self._get_running_container()

        try:
            # 讀取備份內容
            with open(backup_file, "r", encoding="utf-8") as f:
                sql_content = f.read()

            # 使用 psql 還原
            env = os.environ.copy()
            env["PGPASSWORD"] = self.db_password

            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    container,
                    "psql",
                    "-U",
                    self.db_user,
                    "-d",
                    self.db_name,
                ],
                input=sql_content,
                capture_output=True,
                text=True,
                timeout=600,
                env=env,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"Database restored from {backup_name}",
                }
            else:
                return {"success": False, "error": f"Restore failed: {result.stderr}"}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Restore timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_backup_config(self) -> Dict[str, Any]:
        """取得備份設定資訊"""
        return {
            "backup_directory": str(self.backup_dir),
            "attachment_backup_directory": str(self.attachment_backup_dir),
            "uploads_directory": str(self.uploads_dir),
            "log_directory": str(self.log_dir),
            "backup_script": str(self.backup_script),
            "script_exists": self.backup_script.exists(),
            "container_name": self._get_running_container() or self.container_name,
            "database_name": self.db_name,
            "database_user": self.db_user,
        }

    # =========================================================================
    # 異地備份設定功能
    # =========================================================================

    def _load_remote_config(self) -> Dict[str, Any]:
        """載入異地備份設定"""
        default_config = {
            "remote_path": None,
            "sync_enabled": False,
            "sync_interval_hours": 24,
            "last_sync_time": None,
            "sync_status": "idle"
        }
        try:
            if self.remote_config_file.exists():
                with open(self.remote_config_file, "r", encoding="utf-8") as f:
                    return {**default_config, **json.load(f)}
        except Exception as e:
            logger.warning(f"載入異地備份設定失敗: {e}")
        return default_config

    def _save_remote_config(self) -> None:
        """儲存異地備份設定"""
        try:
            self.remote_config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.remote_config_file, "w", encoding="utf-8") as f:
                json.dump(self._remote_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"儲存異地備份設定失敗: {e}")

    async def get_remote_config(self) -> Dict[str, Any]:
        """取得異地備份設定"""
        return self._remote_config.copy()

    async def update_remote_config(
        self,
        remote_path: str,
        sync_enabled: bool = True,
        sync_interval_hours: int = 24
    ) -> Dict[str, Any]:
        """更新異地備份設定"""
        # 驗證路徑
        remote_path_obj = Path(remote_path)

        # 更新設定
        self._remote_config.update({
            "remote_path": str(remote_path),
            "sync_enabled": sync_enabled,
            "sync_interval_hours": sync_interval_hours
        })
        self._save_remote_config()

        # 記錄日誌
        await self._log_backup_operation(
            action="config_update",
            status="success",
            details=f"異地備份路徑設定為: {remote_path}",
            operator="admin"
        )

        return {"success": True, "config": self._remote_config}

    async def sync_to_remote(self) -> Dict[str, Any]:
        """同步備份到異地路徑"""
        if not self._remote_config.get("remote_path"):
            return {"success": False, "error": "未設定異地備份路徑"}

        remote_path = Path(self._remote_config["remote_path"])
        start_time = datetime.now()

        try:
            # 更新同步狀態
            self._remote_config["sync_status"] = "syncing"
            self._save_remote_config()

            # 確保遠端目錄存在
            remote_db_dir = remote_path / "database"
            remote_att_dir = remote_path / "attachments"
            remote_db_dir.mkdir(parents=True, exist_ok=True)
            remote_att_dir.mkdir(parents=True, exist_ok=True)

            synced_files = 0
            total_size = 0

            # 同步資料庫備份
            for backup_file in self.backup_dir.glob("ck_missive_backup_*.sql"):
                dest_file = remote_db_dir / backup_file.name
                if not dest_file.exists() or backup_file.stat().st_mtime > dest_file.stat().st_mtime:
                    shutil.copy2(backup_file, dest_file)
                    synced_files += 1
                    total_size += backup_file.stat().st_size

            # 同步附件備份
            for backup_dir in self.attachment_backup_dir.glob("attachments_backup_*"):
                if backup_dir.is_dir():
                    dest_dir = remote_att_dir / backup_dir.name
                    if not dest_dir.exists():
                        shutil.copytree(backup_dir, dest_dir)
                        synced_files += 1
                        total_size += sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file())

            # 更新同步狀態
            duration = (datetime.now() - start_time).total_seconds()
            self._remote_config["last_sync_time"] = datetime.now().isoformat()
            self._remote_config["sync_status"] = "idle"
            self._save_remote_config()

            # 記錄日誌
            await self._log_backup_operation(
                action="sync",
                status="success",
                details=f"同步 {synced_files} 個檔案到 {remote_path}",
                file_size_kb=round(total_size / 1024, 2),
                duration_seconds=round(duration, 2),
                operator="admin"
            )

            return {
                "success": True,
                "synced_files": synced_files,
                "total_size_kb": round(total_size / 1024, 2),
                "duration_seconds": round(duration, 2),
                "remote_path": str(remote_path)
            }

        except Exception as e:
            self._remote_config["sync_status"] = "error"
            self._save_remote_config()

            await self._log_backup_operation(
                action="sync",
                status="failed",
                details=f"同步失敗: {str(e)}",
                error_message=str(e),
                operator="admin"
            )

            return {"success": False, "error": str(e)}

    # =========================================================================
    # 備份日誌功能
    # =========================================================================

    def _load_backup_logs(self) -> List[Dict[str, Any]]:
        """載入備份日誌"""
        try:
            if self.backup_log_file.exists():
                with open(self.backup_log_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"載入備份日誌失敗: {e}")
        return []

    def _save_backup_logs(self) -> None:
        """儲存備份日誌"""
        try:
            self.backup_log_file.parent.mkdir(parents=True, exist_ok=True)
            # 只保留最近 1000 筆日誌
            logs_to_save = self._backup_logs[-1000:]
            with open(self.backup_log_file, "w", encoding="utf-8") as f:
                json.dump(logs_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"儲存備份日誌失敗: {e}")

    async def _log_backup_operation(
        self,
        action: str,
        status: str,
        details: Optional[str] = None,
        backup_name: Optional[str] = None,
        file_size_kb: Optional[float] = None,
        duration_seconds: Optional[float] = None,
        error_message: Optional[str] = None,
        operator: Optional[str] = None
    ) -> None:
        """記錄備份操作日誌"""
        log_entry = {
            "id": len(self._backup_logs) + 1,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "status": status,
            "details": details,
            "backup_name": backup_name,
            "file_size_kb": file_size_kb,
            "duration_seconds": duration_seconds,
            "error_message": error_message,
            "operator": operator
        }
        self._backup_logs.append(log_entry)
        self._save_backup_logs()

    async def get_backup_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        action_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """查詢備份日誌"""
        logs = self._backup_logs.copy()

        # 篩選
        if action_filter:
            logs = [log for log in logs if log.get("action") == action_filter]
        if status_filter:
            logs = [log for log in logs if log.get("status") == status_filter]
        if date_from:
            logs = [log for log in logs if log.get("timestamp", "") >= date_from]
        if date_to:
            logs = [log for log in logs if log.get("timestamp", "") <= date_to]

        # 倒序排列 (最新的在前)
        logs = list(reversed(logs))

        # 分頁
        total = len(logs)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_logs = logs[start_idx:end_idx]

        return {
            "logs": paged_logs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }


# 單例模式
backup_service = BackupService()
