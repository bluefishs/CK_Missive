"""
附件備份模組
提供附件增量備份、清理、同步功能

@version 1.0.0
@date 2026-02-21
"""

import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AttachmentBackupMixin:
    """附件備份 Mixin - 增量備份、清理相關方法"""

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
                    if (
                        src_stat.st_mtime > dest_stat.st_mtime
                        or src_stat.st_size != dest_stat.st_size
                    ):
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
                file_manifest.append(
                    {
                        "path": str(rel_path),
                        "size": src_file.stat().st_size,
                        "mtime": src_file.stat().st_mtime,
                        "copied": need_copy,
                    }
                )

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
                f.stat().st_size
                for f in latest_backup_path.rglob("*")
                if f.is_file()
            )

            # 儲存 manifest（用於審計追蹤）
            manifest_data = {
                "timestamp": timestamp,
                "total_files": file_count,
                "copied_count": copied_count,
                "skipped_count": skipped_count,
                "removed_count": removed_count,
                "copied_size_mb": round(total_copied_size / (1024 * 1024), 2),
                "total_size_bytes": total_size,
                "files": file_manifest,
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
                "mode": "incremental",
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
