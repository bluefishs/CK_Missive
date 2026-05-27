"""
資料庫備份/還原模組
提供 PostgreSQL pg_dump/pg_restore 備份與還原功能

L49 (2026-05-27): 從 docker CLI subprocess 改 pg_dump 直連
- 觸發：OA-3 PM2 廢除後 backend 入 docker container → docker CLI 不可用
- 修法：backend image 加裝 postgresql-client，pg_dump 走 docker network 直連 postgres:5432
- backwards-compat：API 回應欄位 docker_available / docker_path 保留（鏡像 pg_dump 值）

@version 2.0.0
@date 2026-05-27
"""

import asyncio
import logging
import os
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DatabaseBackupMixin:
    """資料庫備份 Mixin - pg_dump/restore 相關方法"""

    def _build_pg_env(self) -> Dict[str, str]:
        """建構帶 PGPASSWORD 的環境變數 dict"""
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_password
        return env

    async def _backup_database(self, timestamp: str) -> Dict[str, Any]:
        """備份資料庫 — pg_dump 直連 PostgreSQL（取代 docker exec）"""
        # 預先檢查 pg_dump 可用性
        if not self._pg_dump_available:
            return {
                "success": False,
                "error": (
                    f"pg_dump 不可用 (路徑: {self._pg_dump_path})，"
                    "請確認 backend image 已安裝 postgresql-client"
                ),
            }

        backup_file = self.backup_dir / f"ck_missive_backup_{timestamp}.sql"

        try:
            result = subprocess.run(
                [
                    self._pg_dump_path,
                    "-h", self.db_host,
                    "-p", str(self.db_port),
                    "-U", self.db_user,
                    "-d", self.db_name,
                    "--no-owner",
                    "--no-acl",
                ],
                capture_output=True,
                text=True,
                timeout=300,
                env=self._build_pg_env(),
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                dump_data = result.stdout or ""
                if not dump_data.strip():
                    return {
                        "success": False,
                        "error": (
                            f"pg_dump 返回空資料 (returncode=0, "
                            f"stderr={result.stderr or 'N/A'})"
                        ),
                    }

                # 寫入備份檔案
                with open(backup_file, "w", encoding="utf-8") as f:
                    f.write(dump_data)

                file_size = backup_file.stat().st_size

                # 備份完整性驗證
                if file_size < 1024:
                    logger.warning(f"備份檔案異常小: {file_size} bytes")

                # 驗證 SQL dump 完整性（檢查結尾標記）
                with open(backup_file, "r", encoding="utf-8") as f:
                    f.seek(max(0, file_size - 500))
                    tail = f.read()
                    if "PostgreSQL database dump complete" not in tail:
                        logger.warning("備份檔案可能不完整: 未找到結尾標記")
                        return {
                            "success": False,
                            "error": "備份檔案不完整（缺少 pg_dump 結尾標記）",
                        }

                return {
                    "success": True,
                    "file": str(backup_file),
                    "filename": backup_file.name,
                    "size_bytes": file_size,
                    "size_kb": round(file_size / 1024, 2),
                }
            else:
                return {
                    "success": False,
                    "error": f"pg_dump failed: {result.stderr}",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Backup timeout (300s)"}
        except FileNotFoundError:
            # pg_dump 不在 PATH，標記為不可用
            self._pg_dump_available = False
            self._docker_available = False  # compat 鏡像
            return {
                "success": False,
                "error": (
                    f"pg_dump 找不到 (路徑: {self._pg_dump_path})，"
                    "請確認 backend image 已安裝 postgresql-client"
                ),
            }
        except Exception as e:
            logger.error("pg_dump backup failed", exc_info=True, extra={"db_host": self.db_host})
            return {"success": False, "error": str(e)}

    async def _backup_database_with_retry(
        self, timestamp: str, max_retries: int = 2, retry_delay: int = 30
    ) -> Dict[str, Any]:
        """帶重試的資料庫備份"""
        last_error = None
        for attempt in range(max_retries + 1):
            result = await self._backup_database(timestamp)
            if result["success"]:
                if attempt > 0:
                    logger.info(f"備份在第 {attempt + 1} 次嘗試成功")
                return result
            last_error = result.get("error", "Unknown error")

            # pg_dump 不可用時不重試（系統級問題，retry 無意義）
            if not self._pg_dump_available:
                return result

            if attempt < max_retries:
                logger.warning(
                    f"備份失敗 (嘗試 {attempt + 1}/{max_retries + 1}): {last_error}，"
                    f"{retry_delay} 秒後重試..."
                )
                await asyncio.sleep(retry_delay)

        return {
            "success": False,
            "error": f"重試 {max_retries} 次後仍失敗: {last_error}",
        }

    async def restore_database(self, backup_name: str) -> Dict[str, Any]:
        """還原資料庫 — psql 直連（取代 docker exec）"""
        backup_file = self.backup_dir / backup_name

        if not backup_file.exists():
            return {"success": False, "error": "Backup file not found"}

        # psql 通常與 pg_dump 同套件，回退到 PATH 搜尋
        import shutil
        psql_path = shutil.which("psql") or "psql"

        try:
            # 讀取備份內容
            with open(backup_file, "r", encoding="utf-8") as f:
                sql_content = f.read()

            result = subprocess.run(
                [
                    psql_path,
                    "-h", self.db_host,
                    "-p", str(self.db_port),
                    "-U", self.db_user,
                    "-d", self.db_name,
                ],
                input=sql_content,
                capture_output=True,
                text=True,
                timeout=600,
                env=self._build_pg_env(),
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"Database restored from {backup_name}",
                }
            else:
                return {
                    "success": False,
                    "error": f"Restore failed: {result.stderr}",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Restore timeout"}
        except FileNotFoundError:
            return {
                "success": False,
                "error": (
                    f"psql 找不到 (路徑: {psql_path})，"
                    "請確認 backend image 已安裝 postgresql-client"
                ),
            }
        except Exception as e:
            logger.error("psql restore failed", exc_info=True, extra={"db_host": self.db_host})
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
            # L49: 不再需要 container 名稱，但保留欄位（語意：目標 DB host）
            "container_name": self.container_name,
            "database_host": self.db_host,
            "database_port": self.db_port,
            "database_name": self.db_name,
            "database_user": self.db_user,
        }

    async def cleanup_orphan_files(self) -> Dict[str, Any]:
        """清理 0-byte 孤立備份檔案"""
        cleaned = []
        for f in self.backup_dir.glob("ck_missive_backup_*.sql"):
            try:
                if f.stat().st_size == 0:
                    f.unlink()
                    cleaned.append(f.name)
                    logger.info(f"已清理 0-byte 孤立檔案: {f.name}")
            except OSError as e:
                logger.warning(f"清理檔案失敗 {f.name}: {e}")

        if cleaned:
            await self._log_backup_operation(
                action="cleanup",
                status="success",
                details=f"清理 {len(cleaned)} 個 0-byte 孤立檔案",
                operator="admin",
            )

        return {"cleaned_count": len(cleaned), "files": cleaned}
