"""
附件備份模組
提供附件增量備份、清理、同步功能

@version 1.0.0
@date 2026-02-21
"""

import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator

logger = logging.getLogger(__name__)


def _safe_rglob(root: Path) -> Iterator[Path]:
    """OSError-tolerant 遞迴走訪（產出語意等同 rglob("*")：目錄與檔案都給）。

    L49 (2026-05-28) 原以 `while True: try: next(rglob_iter) except OSError: continue`
    實作，**那個容錯從來沒有生效過**：包住的是 generator，而 generator 一旦
    拋出非 StopIteration 的例外就進入 closed 狀態，後續 next() 只會拿到
    StopIteration ⇒ 第一個壞 entry 就是掃描的終點，日誌卻只留一行
    「跳過無法讀取的 entry」，看起來像只漏了一個。

    A38 (2026-08-28) 容器內實測：走訪 233 entry 後停在 2026/02/doc_884，
    warning 1 次（doc_885 Errno 5），manifest 記 total_files=120，
    而 os.walk 實際可掃到 1,550 檔 ⇒ 1,430 檔靜默消失。

    改用 os.walk(onerror=…)：壞目錄由 onerror 記錄後**跳過該子樹並繼續**，
    這才是原本宣稱的行為。回歸測試見
    tests/test_attachment_backup_rglob_regression.py。
    """

    def _on_error(err: OSError) -> None:
        logger.warning(f"_safe_rglob 跳過無法讀取的目錄: {err}")

    for dirpath, dirnames, filenames in os.walk(root, onerror=_on_error):
        base = Path(dirpath)
        for name in dirnames:
            yield base / name
        for name in filenames:
            yield base / name


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

        # L49: OSError-tolerant rglob（host mount 長中文檔名安全）
        file_count = sum(1 for f in _safe_rglob(self.uploads_dir) if f.is_file())

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

            # 增量複製：只複製新增或修改的檔案（L49: OSError-tolerant）
            for src_file in _safe_rglob(self.uploads_dir):
                try:
                    if not src_file.is_file():
                        continue
                except OSError:
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

            # 清理已刪除的檔案（在備份但不在來源）— L49: OSError-tolerant
            removed_count = 0
            for dest_file in _safe_rglob(latest_backup_path):
                try:
                    if not dest_file.is_file():
                        continue
                except OSError:
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

            # 計算最終備份大小 — L49: OSError-tolerant stat
            total_size = 0
            for f in _safe_rglob(latest_backup_path):
                try:
                    if f.is_file():
                        total_size += f.stat().st_size
                except OSError:
                    continue

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

    @staticmethod
    def _safe_mtime(f: Path) -> float:
        """安全取得檔案修改時間（無法讀取時回傳 0，視為最舊）"""
        try:
            return f.stat().st_mtime
        except OSError:
            return 0.0

    async def _cleanup_old_backups(self, retention_days: int) -> None:
        """
        清理過期備份

        策略：
        - 資料庫：刪除超過 retention_days 的 .sql 檔案，至少保留 1 個
        - 附件：保留 attachments_latest（增量備份），清理舊的 manifest
        - 舊版附件目錄：清理遺留的 attachments_backup_* 目錄，至少保留 1 個
        """
        cutoff = datetime.now() - timedelta(days=retention_days)

        # 清理資料庫備份 — 至少保留 1 個（防止備份失敗期間全部清空）
        db_backups = sorted(
            self.backup_dir.glob("ck_missive_backup_*.sql"),
            key=self._safe_mtime,
            reverse=True,
        )
        for backup_file in db_backups[1:]:  # 跳過最新的 1 個
            try:
                if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff:
                    backup_file.unlink()
                    logger.info(f"已清理過期資料庫備份: {backup_file.name}")
            except OSError as e:
                logger.warning(f"清理資料庫備份失敗: {backup_file.name}: {e}")

        # 清理舊版附件備份目錄（遺留的 attachments_backup_* 目錄）— 至少保留 1 個
        att_dirs = sorted(
            (d for d in self.attachment_backup_dir.glob("attachments_backup_*") if d.is_dir()),
            key=self._safe_mtime,
            reverse=True,
        )
        for backup_dir in att_dirs[1:]:  # 跳過最新的 1 個
            try:
                if datetime.fromtimestamp(backup_dir.stat().st_mtime) < cutoff:
                    shutil.rmtree(backup_dir)
                    logger.info(f"已清理舊版附件備份目錄: {backup_dir.name}")
            except (PermissionError, OSError) as e:
                logger.warning(f"清理附件備份目錄失敗: {backup_dir.name}: {e}")

        # 清理過期的 manifest 檔案（保留 retention_days 天內的）
        for manifest_file in self.attachment_backup_dir.glob("manifest_*.json"):
            try:
                if datetime.fromtimestamp(manifest_file.stat().st_mtime) < cutoff:
                    manifest_file.unlink()
                    logger.debug(f"已清理過期 manifest: {manifest_file.name}")
            except OSError:
                pass
