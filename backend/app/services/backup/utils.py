"""
備份服務工具模組
提供 Docker 偵測、路徑工具、環境設定載入、日誌基礎設施

@version 1.0.0
@date 2026-02-21
"""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class BackupUtilsMixin:
    """備份工具 Mixin - Docker 偵測、路徑、環境設定、日誌"""

    def _init_utils(self) -> None:
        """初始化工具層（由 BackupService.__init__ 呼叫）"""
        # 自動偵測執行環境並設定正確的路徑
        if Path("/app").exists() and Path("/app/main.py").exists():
            self.project_root: Path = Path("/app")
        elif Path("/app").exists() and Path("/app/backend").exists():
            self.project_root = Path("/app")
        else:
            self.project_root = Path(__file__).resolve().parent.parent.parent.parent

        # 備份目錄
        self.backup_dir = self.project_root / "backups" / "database"
        self.attachment_backup_dir = self.project_root / "backups" / "attachments"
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

        # Docker CLI 路徑偵測
        self._docker_path: str = self._find_docker_path()
        self._docker_available: bool = self._check_docker_available()
        if self._docker_available:
            logger.info(f"Docker CLI 可用: {self._docker_path}")
        else:
            logger.warning(
                f"Docker CLI 不可用 (路徑: {self._docker_path})，資料庫備份功能將無法使用"
            )

        # 異地備份設定
        self.remote_config_file = self.project_root / "config" / "remote_backup.json"
        self._remote_config: Dict[str, Any] = self._load_remote_config()

        # 備份日誌檔案
        self.backup_log_file = self.log_dir / "backup_operations.json"
        self._backup_logs: List[Dict[str, Any]] = self._load_backup_logs()

        # 確保目錄存在
        self._ensure_directories()

    # =========================================================================
    # 環境設定
    # =========================================================================

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

    # =========================================================================
    # Docker 偵測
    # =========================================================================

    def _find_docker_path(self) -> str:
        """查找 Docker CLI 的完整路徑"""
        # 優先使用 shutil.which（搜尋系統 PATH）
        docker_path = shutil.which("docker")
        if docker_path:
            return docker_path

        # Windows 常見安裝路徑回退
        common_paths = [
            r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
            r"C:\ProgramData\DockerDesktop\version-bin\docker.exe",
        ]
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"在常見路徑找到 Docker CLI: {path}")
                return path

        # Linux/macOS 常見路徑
        for path in ["/usr/bin/docker", "/usr/local/bin/docker"]:
            if Path(path).exists():
                return path

        return "docker"  # 回退到系統 PATH 查找

    def _check_docker_available(self) -> bool:
        """檢查 Docker 是否可用"""
        try:
            result = subprocess.run(
                [self._docker_path, "info"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_running_container(self) -> Optional[str]:
        """取得正在執行的 PostgreSQL 容器名稱"""
        try:
            result = subprocess.run(
                [
                    self._docker_path,
                    "ps",
                    "--filter",
                    f"name={self.container_name}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0 and result.stdout.strip():
                for name in result.stdout.strip().split("\n"):
                    if name.strip() == self.container_name:
                        return self.container_name
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return self.container_name

    def get_environment_status(self) -> Dict[str, Any]:
        """取得備份環境狀態（供前端顯示）"""
        # 重新檢查 Docker 可用性
        self._docker_available = self._check_docker_available()

        # 取得最後成功備份時間
        last_success_time = None
        consecutive_failures = 0
        for log in reversed(self._backup_logs):
            if log.get("action") == "create":
                if log.get("status") == "success":
                    last_success_time = log.get("timestamp")
                    break
                else:
                    consecutive_failures += 1

        return {
            "docker_available": self._docker_available,
            "docker_path": self._docker_path,
            "last_success_time": last_success_time,
            "consecutive_failures": consecutive_failures,
            "backup_dir_exists": self.backup_dir.exists(),
            "uploads_dir_exists": self.uploads_dir.exists(),
        }

    # =========================================================================
    # 異地備份設定
    # =========================================================================

    def _load_remote_config(self) -> Dict[str, Any]:
        """載入異地備份設定"""
        default_config: Dict[str, Any] = {
            "remote_path": None,
            "sync_enabled": False,
            "sync_interval_hours": 24,
            "last_sync_time": None,
            "sync_status": "idle",
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

    # =========================================================================
    # 備份日誌
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
        operator: Optional[str] = None,
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
            "operator": operator,
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
        date_to: Optional[str] = None,
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
            "total_pages": total_pages,
        }
