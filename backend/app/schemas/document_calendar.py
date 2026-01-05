"""
Pydantic schemas for Document Calendar Integration
所有查詢操作使用 POST 機制，符合資安要求
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

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
    priority: Optional[int] = Field(None, description="優先級 (1-5)")
    keyword: Optional[str] = Field(None, description="關鍵字搜尋")
    page: Optional[int] = Field(1, ge=1, description="頁碼")
    page_size: Optional[int] = Field(50, ge=1, le=100, description="每頁筆數")

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

class UserEventsRequest(BaseModel):
    """使用者事件查詢請求"""
    user_id: int = Field(..., description="使用者 ID")
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="結束日期 (YYYY-MM-DD)")

class DocumentCalendarEventCreate(BaseModel):
    """Schema for creating a document calendar event"""
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: Optional[bool] = False
    event_type: Optional[str] = "reminder"
    priority: Optional[int] = 3
    location: Optional[str] = None
    document_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    reminder_enabled: Optional[bool] = True
    reminder_minutes: Optional[int] = 60

class DocumentCalendarEventUpdate(BaseModel):
    """Schema for updating a document calendar event (POST 機制)"""
    event_id: int = Field(..., description="事件 ID")
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    all_day: Optional[bool] = None
    event_type: Optional[str] = None
    priority: Optional[int] = None
    location: Optional[str] = None
    assigned_user_id: Optional[int] = None
    reminder_enabled: Optional[bool] = None
    reminder_minutes: Optional[int] = None

class DocumentCalendarEventResponse(BaseModel):
    """Schema for calendar event response"""
    id: int
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    all_day: bool
    event_type: str
    priority: int
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