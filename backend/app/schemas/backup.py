"""
Pydantic schemas for Backup Management
備份管理相關的統一 Schema 定義
"""
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
