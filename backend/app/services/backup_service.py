"""
備份服務向後相容模組

此檔案為向後相容 shim，實際實作已遷移至 app.services.backup 套件。
所有新程式碼應改用：
    from app.services.backup import BackupService, backup_service

@version 3.0.0
@date 2026-02-21
@deprecated 使用 app.services.backup 替代
"""

from app.services.backup import BackupService, backup_service

__all__ = ["BackupService", "backup_service"]
