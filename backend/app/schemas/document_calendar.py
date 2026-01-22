"""
Pydantic schemas for Document Calendar Integration
所有查詢操作使用 POST 機制，符合資安要求

@version 1.1.0
@date 2026-01-21
@changelog 修正 priority 欄位類型為 str 以與資料庫 VARCHAR 一致
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# ============================================================================
# 共用 Validator
# ============================================================================

def normalize_priority(v):
    """將 priority 正規化為字串（接受 int 或 str 輸入）"""
    if v is not None:
        return str(v)
    return v

class SyncStatusResponse(BaseModel):
    success: bool
    message: str
    google_event_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# ============================================================================
# 事件查詢請求 Schema (POST 機制)
# ============================================================================

class EventListRequest(BaseModel):
    """事件列表查詢請求"""
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="結束日期 (YYYY-MM-DD)")
    event_type: Optional[str] = Field(None, description="事件類型")
    priority: Optional[str] = Field(None, description="優先級 (1-5)")
    keyword: Optional[str] = Field(None, description="關鍵字搜尋")
    document_id: Optional[int] = Field(None, description="關聯公文 ID")
    page: Optional[int] = Field(1, ge=1, description="頁碼")
    page_size: Optional[int] = Field(50, ge=1, le=100, description="每頁筆數")

    @field_validator('priority', mode='before')
    @classmethod
    def _normalize_priority(cls, v):
        return normalize_priority(v)

class EventDetailRequest(BaseModel):
    """事件詳情請求"""
    event_id: int = Field(..., description="事件 ID")

class EventDeleteRequest(BaseModel):
    """事件刪除請求"""
    event_id: int = Field(..., description="事件 ID")
    confirm: bool = Field(False, description="確認刪除")

class EventSyncRequest(BaseModel):
    """事件同步請求"""
    event_id: int = Field(..., description="事件 ID")
    force_sync: bool = Field(False, description="強制同步（即使已同步過）")

class BulkSyncRequest(BaseModel):
    """批次同步請求"""
    event_ids: Optional[List[int]] = Field(None, description="要同步的事件 ID 列表")
    sync_all_pending: bool = Field(True, description="是否同步所有未同步的事件")

class UserEventsRequest(BaseModel):
    """使用者事件查詢請求"""
    user_id: int = Field(..., description="使用者 ID")
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="結束日期 (YYYY-MM-DD)")

class ReminderConfig(BaseModel):
    """提醒設定"""
    minutes_before: int = Field(..., description="提前多少分鐘提醒")
    notification_type: str = Field("system", description="通知類型 (email/system)")

class DocumentCalendarEventCreate(BaseModel):
    """Schema for creating a document calendar event"""
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: Optional[bool] = False
    event_type: Optional[str] = "reminder"
    priority: Optional[str] = "3"
    location: Optional[str] = None
    document_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    reminder_enabled: Optional[bool] = True
    reminder_minutes: Optional[int] = 60

    @field_validator('priority', mode='before')
    @classmethod
    def _normalize_priority(cls, v):
        return normalize_priority(v)

class IntegratedEventCreate(BaseModel):
    """整合式事件建立 (事件+提醒+同步一站完成)"""
    title: str = Field(..., description="事件標題")
    description: Optional[str] = Field(None, description="事件描述")
    start_date: datetime = Field(..., description="開始時間")
    end_date: Optional[datetime] = Field(None, description="結束時間")
    all_day: bool = Field(False, description="是否為全天事件")
    event_type: str = Field("reminder", description="事件類型")
    priority: str = Field("3", description="優先級 (1-5)")
    location: Optional[str] = Field(None, description="地點")
    document_id: Optional[int] = Field(None, description="關聯公文 ID")
    reminder_enabled: bool = Field(True, description="是否啟用提醒")
    reminders: List[ReminderConfig] = Field(default_factory=list, description="提醒設定列表")
    sync_to_google: bool = Field(False, description="是否同步至 Google Calendar")

    @field_validator('priority', mode='before')
    @classmethod
    def _normalize_priority(cls, v):
        return normalize_priority(v)

class DocumentCalendarEventUpdate(BaseModel):
    """Schema for updating a document calendar event (POST 機制)"""
    event_id: int = Field(..., description="事件 ID")
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    all_day: Optional[bool] = None
    event_type: Optional[str] = None
    priority: Optional[str] = None
    location: Optional[str] = None
    document_id: Optional[int] = None  # 新增：關聯公文 ID
    assigned_user_id: Optional[int] = None
    reminder_enabled: Optional[bool] = None
    reminder_minutes: Optional[int] = None

    @field_validator('priority', mode='before')
    @classmethod
    def _normalize_priority(cls, v):
        return normalize_priority(v)

class DocumentCalendarEventResponse(BaseModel):
    """Schema for calendar event response"""
    id: int
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: bool
    event_type: str
    priority: str  # 資料庫欄位為 VARCHAR
    location: Optional[str] = None
    document_id: Optional[int] = None
    doc_number: Optional[str] = None
    assigned_user_id: Optional[int] = None
    created_by: Optional[int] = None
    google_event_id: Optional[str] = None
    google_sync_status: Optional[str] = None
    reminder_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 衝突檢查與同步設定 Schema
# ============================================================================

class ConflictCheckRequest(BaseModel):
    """衝突檢查請求"""
    start_date: str = Field(..., description="開始日期時間 (ISO format)")
    end_date: str = Field(..., description="結束日期時間 (ISO format)")
    exclude_event_id: Optional[int] = Field(None, description="排除的事件 ID")


class SyncIntervalRequest(BaseModel):
    """同步間隔設定請求"""
    interval_seconds: int = Field(..., ge=60, description="同步間隔秒數（最小 60 秒）")