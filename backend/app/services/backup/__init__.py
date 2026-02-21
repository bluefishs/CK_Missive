"""
備份服務套件
提供資料庫與附件的備份、還原、列表與管理功能
支援異地備份路徑設定與備份日誌記錄

@version 3.0.0
@date 2026-02-21

變更記錄:
- v3.0.0: 拆分為模組化套件 (utils, db_backup, attachment_backup, scheduler)
- v2.0.0: Docker PATH 自動偵測、備份重試機制、完整性驗證、manifest 修正
- v1.1.0: Bug 修復（stdout None、manifest 欄位、list_backups 錯誤處理）
"""

from .utils import BackupUtilsMixin
from .db_backup import DatabaseBackupMixin
from .attachment_backup import AttachmentBackupMixin
from .scheduler import BackupSchedulerMixin


class BackupService(
    BackupUtilsMixin,
    DatabaseBackupMixin,
    AttachmentBackupMixin,
    BackupSchedulerMixin,
):
    """備份服務類別

    組合以下模組：
    - BackupUtilsMixin: Docker 偵測、路徑工具、環境設定、日誌基礎設施
    - DatabaseBackupMixin: PostgreSQL pg_dump/restore 備份與還原
    - AttachmentBackupMixin: 附件增量備份與清理
    - BackupSchedulerMixin: 備份建立/列表/刪除、異地同步
    """

    def __init__(self) -> None:
        """初始化備份服務"""
        self._init_utils()


# 單例模式
backup_service = BackupService()

__all__ = ["BackupService", "backup_service"]
