"""
異地備份同步模組
提供備份檔案同步到異地路徑的功能，包含 SMB 長路徑處理

@version 1.0.0
@date 2026-03-19
"""

import hashlib
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RemoteSyncerMixin:
    """異地備份同步 Mixin - 同步備份到遠端路徑、SMB 長路徑處理"""

    # Windows SMB/NAS 路徑上限（中文 UTF-8 3 bytes/char，保守設 180）
    _SMB_MAX_PATH = 180

    @staticmethod
    def _safe_copy2(src: Path, dest: Path) -> None:
        """
        安全複製檔案，處理 Windows SMB 中文長檔名路徑限制。

        Windows SMB/NAS 對 UTF-8 中文路徑有約 200 字元上限，
        超過時自動截斷檔名（保留副檔名和前綴 UUID）。
        """
        dest_str = str(dest)

        if os.name == "nt" and len(dest_str) > RemoteSyncerMixin._SMB_MAX_PATH:
            # 計算目錄路徑長度，截斷檔名
            dest_dir = str(dest.parent)
            ext = dest.suffix
            stem = dest.stem
            max_name_len = RemoteSyncerMixin._SMB_MAX_PATH - len(dest_dir) - 1  # -1 for separator
            if max_name_len < 10:
                raise OSError(f"目錄路徑過長，無法截斷檔名: {dest_dir}")
            # 用原始檔名 hash 前 6 碼防碰撞
            name_hash = hashlib.md5(stem.encode("utf-8")).hexdigest()[:6]
            truncated_stem = stem[: max_name_len - len(ext) - 8] + f"_{name_hash}"
            dest = Path(dest_dir) / (truncated_stem + ext)
            logger.debug(
                f"SMB 長路徑截斷: {len(dest_str)} → {len(str(dest))} chars"
            )

        shutil.copy2(str(src), str(dest))

    async def sync_to_remote(self) -> Dict[str, Any]:
        """同步備份到異地路徑"""
        if not self._remote_config.get("remote_path"):
            return {"success": False, "error": "未設定異地備份路徑"}

        remote_path = Path(self._remote_config["remote_path"])
        start_time = datetime.now()

        # 驗證遠端路徑可存取（磁碟掛載、權限等）
        try:
            # Windows 網路磁碟：先檢查根路徑（如 Z:\）是否存在
            root = remote_path.anchor or remote_path.parts[0] if remote_path.parts else ""
            if root and not Path(root).exists():
                error_msg = f"遠端磁碟 {root} 不可存取（磁碟未掛載或路徑無效）"
                self._remote_config["sync_status"] = "error"
                self._save_remote_config()
                await self._log_backup_operation(
                    action="sync", status="failed",
                    details=error_msg, error_message=error_msg, operator="system",
                )
                return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"路徑驗證失敗: {e}"
            self._remote_config["sync_status"] = "error"
            self._save_remote_config()
            return {"success": False, "error": error_msg}

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
            failed_files: List[str] = []

            # 同步資料庫備份
            for backup_file in self.backup_dir.glob("ck_missive_backup_*.sql"):
                dest_file = remote_db_dir / backup_file.name
                try:
                    if (
                        not dest_file.exists()
                        or backup_file.stat().st_mtime > dest_file.stat().st_mtime
                    ):
                        self._safe_copy2(backup_file, dest_file)
                        synced_files += 1
                        total_size += backup_file.stat().st_size
                except OSError as e:
                    logger.warning(f"同步資料庫備份失敗: {backup_file.name}: {e}")
                    failed_files.append(f"DB:{backup_file.name}")

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
                        try:
                            if src_file.stat().st_mtime > dest_file.stat().st_mtime:
                                need_copy = True
                        except OSError:
                            need_copy = True

                    if need_copy:
                        try:
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            self._safe_copy2(src_file, dest_file)
                            synced_files += 1
                            total_size += src_file.stat().st_size
                        except OSError as e:
                            logger.warning(
                                f"同步附件失敗 (路徑長度 {len(str(dest_file))}): "
                                f"{rel_path}: {e}"
                            )
                            failed_files.append(str(rel_path))

                # 清理遠端已刪除的檔案
                for dest_file in remote_latest.rglob("*"):
                    if not dest_file.is_file():
                        continue
                    rel_path = dest_file.relative_to(remote_latest)
                    src_file = latest_backup / rel_path
                    if not src_file.exists():
                        try:
                            dest_file.unlink()
                        except OSError:
                            pass
                        try:
                            dest_file.parent.rmdir()
                        except OSError:
                            pass
            else:
                # 向後相容：同步舊版完整備份目錄
                for backup_dir in self.attachment_backup_dir.glob(
                    "attachments_backup_*"
                ):
                    if backup_dir.is_dir():
                        dest_dir = remote_att_dir / backup_dir.name
                        if not dest_dir.exists():
                            try:
                                shutil.copytree(backup_dir, dest_dir)
                                synced_files += 1
                                total_size += sum(
                                    f.stat().st_size
                                    for f in backup_dir.rglob("*")
                                    if f.is_file()
                                )
                            except OSError as e:
                                logger.warning(f"同步舊版附件備份失敗: {backup_dir.name}: {e}")
                                failed_files.append(f"DIR:{backup_dir.name}")

            # 更新同步狀態
            duration = (datetime.now() - start_time).total_seconds()
            self._remote_config["last_sync_time"] = datetime.now().isoformat()
            self._remote_config["sync_status"] = "idle"
            self._save_remote_config()

            # 記錄日誌
            fail_note = f"，{len(failed_files)} 個失敗" if failed_files else ""
            await self._log_backup_operation(
                action="sync",
                status="success" if not failed_files else "partial",
                details=f"同步 {synced_files} 個檔案到 {remote_path}{fail_note}",
                file_size_kb=round(total_size / 1024, 2),
                duration_seconds=round(duration, 2),
                error_message=f"失敗檔案: {', '.join(failed_files[:10])}" if failed_files else None,
                operator="admin",
            )

            result: Dict[str, Any] = {
                "success": True,
                "synced_files": synced_files,
                "total_size_kb": round(total_size / 1024, 2),
                "duration_seconds": round(duration, 2),
                "remote_path": str(remote_path),
            }
            if failed_files:
                result["failed_files"] = failed_files[:20]
                result["failed_count"] = len(failed_files)

            return result

        except Exception as e:
            self._remote_config["sync_status"] = "error"
            self._save_remote_config()

            await self._log_backup_operation(
                action="sync",
                status="failed",
                details=f"同步失敗: {str(e)}",
                error_message=str(e),
                operator="admin",
            )

            return {"success": False, "error": str(e)}
