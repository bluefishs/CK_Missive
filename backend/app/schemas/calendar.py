"""
行事曆相關的 Pydantic 模型
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator # 新增 ConfigDict, field_validator
from enum import Enum


class EventStatus(str, Enum):
    """事件狀態"""
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class SyncStatus(str, Enum):
    """同步狀態"""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


class CalendarEventBase(BaseModel):
    """行事曆事件基礎模型"""
    title: str = Field(..., min_length=1, max_length=200, description="事件標題")
    description: Optional[str] = Field(None, description="事件描述")
    location: Optional[str] = Field(None, max_length=500, description="事件地點")
    start_datetime: datetime = Field(..., description="開始時間")
    end_datetime: datetime = Field(..., description="結束時間")
    timezone: Optional[str] = Field("Asia/Taipei", description="時區")
    is_all_day: Optional[bool] = Field(False, description="是否為全天事件")
    reminders: Optional[List[Dict[str, Any]]] = Field(None, description="提醒設定")
    attendees: Optional[List[Dict[str, Any]]] = Field(None, description="與會者列表")
    visibility: Optional[str] = Field("private", description="可見性")
    
    @field_validator('end_datetime') # 使用 field_validator
    @classmethod
    def end_after_start(cls, v, info): # info 替代 values
        if 'start_datetime' in info.data and v <= info.data['start_datetime']:
            raise ValueError('結束時間必須晚於開始時間')
        return v


class CalendarEventCreate(CalendarEventBase):
    """建立行事曆事件"""
    document_id: Optional[int] = Field(None, description="關聯公文ID")
    contract_case_id: Optional[int] = Field(None, description="關聯承攬案件ID")


class CalendarEventUpdate(BaseModel):
    """更新行事曆事件"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="事件標題")
    description: Optional[str] = Field(None, description="事件描述")
    location: Optional[str] = Field(None, max_length=500, description="事件地點")
    start_datetime: Optional[datetime] = Field(None, description="開始時間")
    end_datetime: Optional[datetime] = Field(None, description="結束時間")
    timezone: Optional[str] = Field(None, description="時區")
    is_all_day: Optional[bool] = Field(None, description="是否為全天事件")
    reminders: Optional[List[Dict[str, Any]]] = Field(None, description="提醒設定")
    attendees: Optional[List[Dict[str, Any]]] = Field(None, description="與會者列表")
    visibility: Optional[str] = Field(None, description="可見性")
    status: Optional[EventStatus] = Field(None, description="事件狀態")
    
    @field_validator('end_datetime') # 使用 field_validator
    @classmethod
    def end_after_start(cls, v, info): # info 替代 values
        if v and 'start_datetime' in info.data and info.data['start_datetime'] and v <= info.data['start_datetime']:
            raise ValueError('結束時間必須晚於開始時間')
        return v


class CalendarEventResponse(CalendarEventBase):
    """行事曆事件回應"""
    id: int
    status: Optional[EventStatus] = None
    google_event_id: Optional[str] = None
    google_sync_status: Optional[SyncStatus] = None
    google_last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    user_id: int
    created_by_id: int
    document_id: Optional[int] = None
    contract_case_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True) # 使用 model_config


class CalendarEventList(BaseModel):
    """行事曆事件列表"""
    events: List[CalendarEventResponse]
    total: int
    page: int
    per_page: int


class GoogleCalendarConnect(BaseModel):
    """Google Calendar 連結請求"""
    auth_url: str


class SyncResponse(BaseModel):
    """同步回應"""
    status: str = Field(..., description="同步狀態")
    message: str = Field(..., description="同步訊息")
    events_synced: Optional[int] = Field(None, description="同步的事件數量")


class CalendarSyncLogResponse(BaseModel):
    """同步日誌回應"""
    id: int
    sync_type: str
    operation: str
    status: SyncStatus
    error_message: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True) # 使用 model_config


class CalendarStats(BaseModel):
    """行事曆統計"""
    total_events: int = Field(..., description="總事件數")
    today_events: int = Field(..., description="今日事件數")
    this_week_events: int = Field(..., description="本週事件數")
    this_month_events: int = Field(..., description="本月事件數")
    upcoming_events: int = Field(..., description="即將到來的事件數")
    google_synced_events: int = Field(..., description="已同步到Google的事件數")


class EventReminder(BaseModel):
    """事件提醒設定"""
    method: str = Field(..., description="提醒方式", pattern="^(email|popup)$") # 將 regex 替換為 pattern
    minutes: int = Field(..., ge=0, description="提前提醒分鐘數")


class EventAttendee(BaseModel):
    """事件與會者"""
    email: str = Field(..., description="與會者郵箱")
    display_name: Optional[str] = Field(None, description="顯示名稱")
    response_status: Optional[str] = Field("needsAction", description="回應狀態")
    optional: Optional[bool] = Field(False, description="是否為可選參與者")


class GoogleWebhookNotification(BaseModel):
    """Google Calendar Webhook 通知"""
    channel_id: str = Field(..., description="通知頻道ID")
    message_number: int = Field(..., description="訊息編號")
    resource_id: str = Field(..., description="資源ID")
    resource_uri: str = Field(..., description="資源URI")
    resource_state: str = Field(..., description="資源狀態")


class CalendarEventFilter(BaseModel):
    """行事曆事件篩選器"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[List[EventStatus]] = None
    has_location: Optional[bool] = None
    has_attendees: Optional[bool] = None
    google_synced_only: Optional[bool] = None
    document_id: Optional[int] = None
    contract_case_id: Optional[int] = None