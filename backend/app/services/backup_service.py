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
        # 自動偵測執行環境並設定正確的路徑
        # Docker 容器內使用 /app，Windows 直接執行使用專案目錄
        if Path("/app").exists() and Path("/app/main.py").exists():
            # Docker 容器環境 (backend 目錄掛載到 /app)
            self.project_root: Path = Path("/app")
        elif Path("/app").exists() and Path("/app/backend").exists():
            # Docker 容器環境 (專案根目錄掛載到 /app)
            self.project_root = Path("/app")
        else:
            # Windows 直接執行環境 - 使用 backend 目錄的父目錄
            self.project_root = Path(__file__).resolve().parent.parent.parent.parent

        # 備份目錄
        self.backup_dir = self.project_root / "backups" / "database"
        self.attachment_backup_dir = self.project_root / "backups" / "attachments"
        # 附件實際儲存在 backend/uploads（相對於後端執行目錄）
        self.uploads_dir = self.project_root / "backend" / "uploads"
        self.log_dir = self.project_root / "logs" / "backup"

        logger.info(f"備份服務初始化 - 專案根目錄: {self.project_root}")

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

        # 記錄備份操作日誌
        db_info = result.get("database_backup", {})
        att_info = result.get("attachments_backup", {})
        details = []
        if db_info.get("success"):
            details.append(f"資料庫: {db_info.get('filename', 'N/A')} ({db_info.get('size_kb', 0)} KB)")
        if att_info.get("success"):
            details.append(f"附件: {att_info.get('file_count', 0)} 檔案 ({att_info.get('size_mb', 0)} MB)")

        await self._log_backup_operation(
            action="create",
            status="success" if result["success"] else "failed",
            details=", ".join(details) if details else "備份失敗",
            backup_name=db_info.get("filename") or att_info.get("dirname"),
            file_size_kb=db_info.get("size_kb"),
            error_message="; ".join(result["errors"]) if result["errors"] else None,
            operator="system"
        )

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
        """
        備份附件（差異/增量備份機制）

        優化策略：
        1. 維護一個主備份目錄 (attachments_latest)
        2. 每次只複製新增/修改的檔案
        3. 避免重複檔案造成空間浪費
        """
        if not self.uploads_dir.exists():
            return {"success": True, "message": "No uploads directory"}

        files = list(self.uploads_dir.rglob("*"))
        file_count = len([f for f in files if f.is_file()])

        if file_count == 0:
            return {"success": True, "message": "No files to backup", "file_count": 0}

        # 使用固定的最新備份目錄（增量更新）
        latest_backup_path = self.attachment_backup_dir / "attachments_latest"
        # 保留時間戳記目錄用於版本紀錄（只記錄 manifest）
        manifest_path = self.attachment_backup_dir / f"manifest_{timestamp}.json"

        try:
            # 確保目錄存在
            latest_backup_path.mkdir(parents=True, exist_ok=True)

            copied_count = 0
            skipped_count = 0
            total_copied_size = 0
            file_manifest = []

            # 增量複製：只複製新增或修改的檔案
            for src_file in self.uploads_dir.rglob("*"):
                if not src_file.is_file():
                    continue

                # 計算相對路徑
                rel_path = src_file.relative_to(self.uploads_dir)
                dest_file = latest_backup_path / rel_path

                # 檢查是否需要複製
                need_copy = False
                if not dest_file.exists():
                    need_copy = True
                else:
                    # 比較修改時間和大小
                    src_stat = src_file.stat()
                    dest_stat = dest_file.stat()
                    if (src_stat.st_mtime > dest_stat.st_mtime or
                        src_stat.st_size != dest_stat.st_size):
                        need_copy = True

                if need_copy:
                    # 確保目標目錄存在
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    copied_count += 1
                    total_copied_size += src_file.stat().st_size
                else:
                    skipped_count += 1

                # 記錄 manifest
                file_manifest.append({
                    "path": str(rel_path),
                    "size": src_file.stat().st_size,
                    "mtime": src_file.stat().st_mtime,
                    "copied": need_copy
                })

            # 清理已刪除的檔案（在備份但不在來源）
            removed_count = 0
            for dest_file in latest_backup_path.rglob("*"):
                if not dest_file.is_file():
                    continue
                rel_path = dest_file.relative_to(latest_backup_path)
                src_file = self.uploads_dir / rel_path
                if not src_file.exists():
                    dest_file.unlink()
                    removed_count += 1
                    # 清理空目錄
                    try:
                        dest_file.parent.rmdir()
                    except OSError:
                        pass  # 目錄非空，忽略

            # 計算最終備份大小
            total_size = sum(
                f.stat().st_size for f in latest_backup_path.rglob("*") if f.is_file()
            )

            # 儲存 manifest（用於審計追蹤）
            manifest_data = {
                "timestamp": timestamp,
                "total_files": file_count,
                "copied": copied_count,
                "skipped": skipped_count,
                "removed": removed_count,
                "total_size_bytes": total_size,
                "files": file_manifest
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)

            # 清理舊的 manifest 檔案（保留最近 30 個）
            manifests = sorted(self.attachment_backup_dir.glob("manifest_*.json"))
            for old_manifest in manifests[:-30]:
                old_manifest.unlink()

            return {
                "success": True,
                "path": str(latest_backup_path),
                "dirname": latest_backup_path.name,
                "file_count": file_count,
                "copied_count": copied_count,
                "skipped_count": skipped_count,
                "removed_count": removed_count,
                "size_bytes": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2),
                "copied_size_mb": round(total_copied_size / (1024 * 1024), 2),
                "mode": "incremental"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _cleanup_old_backups(self, retention_days: int) -> None:
        """
        清理過期備份

        策略：
        - 資料庫：刪除超過 retention_days 的 .sql 檔案
        - 附件：保留 attachments_latest（增量備份），清理舊的 manifest
        - 舊版附件目錄：清理遺留的 attachments_backup_* 目錄
        """
        cutoff = datetime.now() - timedelta(days=retention_days)

        # 清理資料庫備份
        for backup_file in self.backup_dir.glob("ck_missive_backup_*.sql"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff:
                backup_file.unlink()
                logger.info(f"已清理過期資料庫備份: {backup_file.name}")

        # 清理舊版附件備份目錄（遺留的 attachments_backup_* 目錄）
        # 新版使用 attachments_latest 增量備份，舊的完整備份目錄可以清理
        for backup_dir in self.attachment_backup_dir.glob("attachments_backup_*"):
            if backup_dir.is_dir():
                if datetime.fromtimestamp(backup_dir.stat().st_mtime) < cutoff:
                    shutil.rmtree(backup_dir)
                    logger.info(f"已清理舊版附件備份目錄: {backup_dir.name}")

        # 清理過期的 manifest 檔案（保留 retention_days 天內的）
        for manifest_file in self.attachment_backup_dir.glob("manifest_*.json"):
            if datetime.fromtimestamp(manifest_file.stat().st_mtime) < cutoff:
                manifest_file.unlink()
                logger.debug(f"已清理過期 manifest: {manifest_file.name}")

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

        # 附件備份列表 - 優先顯示增量備份 (attachments_latest)
        latest_backup_dir = self.attachment_backup_dir / "attachments_latest"
        if latest_backup_dir.exists() and latest_backup_dir.is_dir():
            stat = latest_backup_dir.stat()
            # 計算目錄大小
            total_size = sum(
                f.stat().st_size for f in latest_backup_dir.rglob("*") if f.is_file()
            )
            file_count = len([f for f in latest_backup_dir.rglob("*") if f.is_file()])

            # 嘗試從最新的 manifest 讀取統計資訊
            manifest_stats = {}
            manifest_files = sorted(
                self.attachment_backup_dir.glob("manifest_*.json"), reverse=True
            )
            if manifest_files:
                try:
                    with open(manifest_files[0], "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)
                        manifest_stats = {
                            "copied_count": manifest_data.get("copied_count", 0),
                            "skipped_count": manifest_data.get("skipped_count", 0),
                            "removed_count": manifest_data.get("removed_count", 0),
                            "copied_size_mb": manifest_data.get("copied_size_mb", 0),
                            "last_sync": manifest_data.get("timestamp", ""),
                        }
                except Exception:
                    pass

            attachment_backups.append(
                {
                    "dirname": "attachments_latest",
                    "path": str(latest_backup_dir),
                    "size_bytes": total_size,
                    "size_mb": round(total_size / (1024 * 1024), 2),
                    "file_count": file_count,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "attachments",
                    "mode": "incremental",
                    **manifest_stats,
                }
            )

        # 舊版完整備份列表（供回溯）
        for backup_dir in sorted(
            self.attachment_backup_dir.glob("attachments_backup_*"), reverse=True
        ):
            if backup_dir.is_dir():
                stat = backup_dir.stat()
                # 計算目錄大小
                total_size = sum(
                    f.stat().st_size for f in backup_dir.rglob("*") if f.is_file()
                )
                file_count = len([f for f in backup_dir.rglob("*") if f.is_file()])

                attachment_backups.append(
                    {
                        "dirname": backup_dir.name,
                        "path": str(backup_dir),
                        "size_bytes": total_size,
                        "size_mb": round(total_size / (1024 * 1024), 2),
                        "file_count": file_count,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": "attachments",
                        "mode": "full",
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
                # 禁止刪除增量備份主目錄（attachments_latest）
                if backup_name == "attachments_latest":
                    return {
                        "success": False,
                        "error": "Cannot delete incremental backup directory. Use full backup instead.",
                    }
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

            # 同步附件備份 - 優先使用增量備份 (attachments_latest)
            latest_backup = self.attachment_backup_dir / "attachments_latest"
            if latest_backup.exists() and latest_backup.is_dir():
                # 增量同步 attachments_latest 目錄
                remote_latest = remote_att_dir / "attachments_latest"
                remote_latest.mkdir(parents=True, exist_ok=True)

                for src_file in latest_backup.rglob("*"):
                    if not src_file.is_file():
                        continue
                    rel_path = src_file.relative_to(latest_backup)
                    dest_file = remote_latest / rel_path

                    # 只複製新增或修改的檔案
                    need_copy = False
                    if not dest_file.exists():
                        need_copy = True
                    else:
                        if src_file.stat().st_mtime > dest_file.stat().st_mtime:
                            need_copy = True

                    if need_copy:
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_file)
                        synced_files += 1
                        total_size += src_file.stat().st_size

                # 清理遠端已刪除的檔案
                for dest_file in remote_latest.rglob("*"):
                    if not dest_file.is_file():
                        continue
                    rel_path = dest_file.relative_to(remote_latest)
                    src_file = latest_backup / rel_path
                    if not src_file.exists():
                        dest_file.unlink()
                        try:
                            dest_file.parent.rmdir()
                        except OSError:
                            pass
            else:
                # 向後相容：同步舊版完整備份目錄
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
