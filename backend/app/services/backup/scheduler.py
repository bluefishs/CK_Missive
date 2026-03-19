"""
備份排程管理模組
提供備份建立/列表/刪除等排程管理功能

異地同步功能已拆分至 remote_syncer.py

@version 1.1.0
@date 2026-03-19
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .remote_syncer import RemoteSyncerMixin

logger = logging.getLogger(__name__)


class BackupSchedulerMixin(RemoteSyncerMixin):
    """備份排程管理 Mixin - 建立/列表/刪除備份

    異地同步功能繼承自 RemoteSyncerMixin。
    """

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
        result: Dict[str, Any] = {
            "success": True,
            "timestamp": timestamp,
            "database_backup": None,
            "attachments_backup": None,
            "errors": [],
        }

        # 資料庫備份（含重試機制）
        if include_database:
            db_result = await self._backup_database_with_retry(timestamp)
            result["database_backup"] = db_result
            if not db_result.get("success"):
                result["errors"].append(db_result.get("error", "資料庫備份失敗"))

        # 附件備份
        if include_attachments:
            att_result = await self._backup_attachments(timestamp)
            result["attachments_backup"] = att_result
            if not att_result.get("success"):
                result["errors"].append(att_result.get("error", "附件備份失敗"))

        # 清理舊備份（僅在至少一項備份成功時執行，避免失敗期間清空所有備份）
        if len(result["errors"]) == 0:
            await self._cleanup_old_backups(retention_days)
        else:
            logger.warning("備份有錯誤，跳過舊備份清理以保護現有備份")

        result["success"] = len(result["errors"]) == 0

        # 記錄備份操作日誌
        db_info = result.get("database_backup") or {}
        att_info = result.get("attachments_backup") or {}
        details = []
        if db_info.get("success"):
            details.append(
                f"資料庫: {db_info.get('filename', 'N/A')} ({db_info.get('size_kb', 0)} KB)"
            )
        if att_info.get("success"):
            details.append(
                f"附件: {att_info.get('file_count', 0)} 檔案 ({att_info.get('size_mb', 0)} MB)"
            )

        await self._log_backup_operation(
            action="create",
            status="success" if result["success"] else "failed",
            details=", ".join(details) if details else "備份失敗",
            backup_name=db_info.get("filename") or att_info.get("dirname"),
            file_size_kb=db_info.get("size_kb"),
            error_message="; ".join(result["errors"]) if result["errors"] else None,
            operator="system",
        )

        return result

    async def list_backups(self) -> Dict[str, Any]:
        """列出所有備份"""
        database_backups = []
        attachment_backups = []

        # 資料庫備份列表
        for backup_file in sorted(
            self.backup_dir.glob("ck_missive_backup_*.sql"), reverse=True
        ):
            try:
                stat = backup_file.stat()
                # 略過 0-byte 的失敗備份檔案
                if stat.st_size == 0:
                    continue
                database_backups.append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size_bytes": stat.st_size,
                        "size_kb": round(stat.st_size / 1024, 2),
                        "created_at": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "type": "database",
                    }
                )
            except OSError as e:
                logger.warning(f"無法讀取備份檔案 {backup_file.name}: {e}")

        # 附件備份列表 - 優先顯示增量備份 (attachments_latest)
        latest_backup_dir = self.attachment_backup_dir / "attachments_latest"
        if latest_backup_dir.exists() and latest_backup_dir.is_dir():
            try:
                stat = latest_backup_dir.stat()
                # 計算目錄大小（安全遍歷，跳過無法讀取的檔案）
                total_size = 0
                file_count = 0
                for f in latest_backup_dir.rglob("*"):
                    if f.is_file():
                        try:
                            total_size += f.stat().st_size
                            file_count += 1
                        except OSError:
                            pass

                # 嘗試從最新的 manifest 讀取統計資訊
                manifest_stats: Dict[str, Any] = {}
                manifest_files = sorted(
                    self.attachment_backup_dir.glob("manifest_*.json"), reverse=True
                )
                if manifest_files:
                    try:
                        with open(manifest_files[0], "r", encoding="utf-8") as f:
                            manifest_data = json.load(f)
                            manifest_stats = {
                                "copied_count": manifest_data.get(
                                    "copied_count",
                                    manifest_data.get("copied", 0),
                                ),
                                "skipped_count": manifest_data.get(
                                    "skipped_count",
                                    manifest_data.get("skipped", 0),
                                ),
                                "removed_count": manifest_data.get(
                                    "removed_count",
                                    manifest_data.get("removed", 0),
                                ),
                                "copied_size_mb": manifest_data.get(
                                    "copied_size_mb", 0
                                ),
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
                        "created_at": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "type": "attachments",
                        "mode": "incremental",
                        **manifest_stats,
                    }
                )
            except OSError as e:
                logger.warning(f"無法讀取增量備份目錄: {e}")

        # 舊版完整備份列表（供回溯）
        for backup_dir in sorted(
            self.attachment_backup_dir.glob("attachments_backup_*"), reverse=True
        ):
            if backup_dir.is_dir():
                try:
                    stat = backup_dir.stat()
                    # 計算目錄大小（安全遍歷）
                    total_size = 0
                    file_count = 0
                    for f in backup_dir.rglob("*"):
                        if f.is_file():
                            try:
                                total_size += f.stat().st_size
                                file_count += 1
                            except OSError:
                                pass

                    attachment_backups.append(
                        {
                            "dirname": backup_dir.name,
                            "path": str(backup_dir),
                            "size_bytes": total_size,
                            "size_mb": round(total_size / (1024 * 1024), 2),
                            "file_count": file_count,
                            "created_at": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "type": "attachments",
                            "mode": "full",
                        }
                    )
                except OSError as e:
                    logger.warning(
                        f"無法讀取附件備份目錄 {backup_dir.name}: {e}"
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
                "total_attachment_size_mb": round(
                    total_att_size / (1024 * 1024), 2
                ),
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

    # =========================================================================
    # 異地備份設定功能 (sync_to_remote 在 RemoteSyncerMixin)
    # =========================================================================

    async def get_remote_config(self) -> Dict[str, Any]:
        """取得異地備份設定"""
        return self._remote_config.copy()

    async def update_remote_config(
        self,
        remote_path: str,
        sync_enabled: bool = True,
        sync_interval_hours: int = 24,
    ) -> Dict[str, Any]:
        """更新異地備份設定"""
        # 驗證路徑可存取
        if sync_enabled and remote_path:
            p = Path(remote_path)
            root = p.anchor or (p.parts[0] if p.parts else "")
            if root and not Path(root).exists():
                return {
                    "success": False,
                    "error": f"路徑 {root} 不可存取（磁碟未掛載），請確認後再啟用同步",
                }

        # 更新設定（啟用時重置錯誤狀態）
        self._remote_config.update(
            {
                "remote_path": str(remote_path),
                "sync_enabled": sync_enabled,
                "sync_interval_hours": sync_interval_hours,
                "sync_status": "idle" if sync_enabled else self._remote_config.get("sync_status", "idle"),
            }
        )
        self._save_remote_config()

        # 記錄日誌
        await self._log_backup_operation(
            action="config_update",
            status="success",
            details=f"異地備份路徑設定為: {remote_path}",
            operator="admin",
        )

        return {"success": True, "config": self._remote_config}
