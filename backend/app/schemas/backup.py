"""
Pydantic schemas for Backup Management
備份管理相關的統一 Schema 定義

@version 1.1.0
@date 2026-01-29
"""
from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# 備份請求 Schema
# =============================================================================

class CreateBackupRequest(BaseModel):
    """建立備份請求"""
    include_database: bool = Field(True, description="是否包含資料庫")
    include_attachments: bool = Field(True, description="是否包含附件")
    retention_days: int = Field(7, ge=1, le=365, description="備份保留天數")


class DeleteBackupRequest(BaseModel):
    """刪除備份請求"""
    backup_name: str = Field(..., description="備份名稱")
    backup_type: str = Field("database", description="備份類型 (database/attachments)")


class RestoreBackupRequest(BaseModel):
    """還原備份請求"""
    backup_name: str = Field(..., description="備份檔案名稱")


# =============================================================================
# 異地備份設定 Schema
# =============================================================================

class RemoteBackupConfigRequest(BaseModel):
    """異地備份路徑設定請求"""
    remote_path: str = Field(..., min_length=1, description="異地備份路徑")
    sync_enabled: bool = Field(True, description="是否啟用同步")
    sync_interval_hours: int = Field(24, ge=1, le=168, description="同步間隔(小時)")


class RemoteBackupConfigResponse(BaseModel):
    """異地備份設定回應"""
    remote_path: Optional[str] = Field(None, description="異地備份路徑")
    sync_enabled: bool = Field(False, description="是否啟用同步")
    sync_interval_hours: int = Field(24, description="同步間隔(小時)")
    last_sync_time: Optional[str] = Field(None, description="最後同步時間")
    sync_status: str = Field("idle", description="同步狀態")


# =============================================================================
# 備份日誌 Schema
# =============================================================================

class BackupLogEntry(BaseModel):
    """備份日誌項目"""
    id: int
    timestamp: str = Field(..., description="時間戳記")
    action: str = Field(..., description="操作類型 (create/delete/restore/sync)")
    status: str = Field(..., description="狀態 (success/failed/in_progress)")
    details: Optional[str] = Field(None, description="詳細資訊")
    backup_name: Optional[str] = Field(None, description="備份名稱")
    file_size_kb: Optional[float] = Field(None, description="檔案大小(KB)")
    duration_seconds: Optional[float] = Field(None, description="執行時間(秒)")
    error_message: Optional[str] = Field(None, description="錯誤訊息")
    operator: Optional[str] = Field(None, description="操作者")


class BackupLogListRequest(BaseModel):
    """備份日誌列表請求"""
    page: int = Field(1, ge=1, description="頁碼")
    page_size: int = Field(20, ge=1, le=100, description="每頁筆數")
    action_filter: Optional[str] = Field(None, description="操作類型篩選")
    status_filter: Optional[str] = Field(None, description="狀態篩選")
    date_from: Optional[str] = Field(None, description="起始日期")
    date_to: Optional[str] = Field(None, description="結束日期")


class BackupLogListResponse(BaseModel):
    """備份日誌列表回應"""
    logs: List[BackupLogEntry]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# 排程器控制 Schema
# =============================================================================

class SchedulerStatusResponse(BaseModel):
    """排程器狀態回應"""
    running: bool = Field(..., description="是否運行中")
    backup_time: str = Field(..., description="備份時間 (HH:MM)")
    next_backup: Optional[str] = Field(None, description="下次備份時間")
    last_backup: Optional[str] = Field(None, description="上次備份時間")
    stats: dict = Field(default_factory=dict, description="統計資訊")
