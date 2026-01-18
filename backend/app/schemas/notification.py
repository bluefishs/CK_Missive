"""
Pydantic schemas for Notifications
通知相關的統一 Schema 定義

包含：
- 系統通知 (System Notifications)
- 專案通知 (Project Notifications)
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# =============================================================================
# 系統通知 Schema (System Notifications)
# =============================================================================

class NotificationQuery(BaseModel):
    """通知查詢參數"""
    is_read: Optional[bool] = Field(None, description="是否已讀")
    severity: Optional[str] = Field(None, description="嚴重程度 (info/warning/error/critical)")
    type: Optional[str] = Field(None, description="通知類型 (system/critical_change/import/error)")
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")


class NotificationItem(BaseModel):
    """通知項目"""
    id: int
    type: str
    severity: str
    title: str
    message: str
    source_table: Optional[str] = None
    source_id: Optional[int] = None
    changes: Optional[dict] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    is_read: bool = False
    read_at: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """通知列表回應"""
    success: bool = True
    items: List[NotificationItem] = []
    total: int = 0
    unread_count: int = 0
    page: int = 1
    limit: int = 20


class MarkReadRequest(BaseModel):
    """標記已讀請求 (批次)"""
    notification_ids: List[int] = Field(..., description="要標記為已讀的通知 ID 列表")


class MarkReadResponse(BaseModel):
    """標記已讀回應"""
    success: bool = True
    updated_count: int = 0
    message: str = ""


class UnreadCountResponse(BaseModel):
    """未讀數量回應"""
    success: bool = True
    unread_count: int = 0


# =============================================================================
# 專案通知 Schema (Project Notifications)
# =============================================================================

class NotificationSettingsRequest(BaseModel):
    """專案通知設定請求"""
    project_id: int
    notification_settings: Dict[str, Any]


class TeamNotificationRequest(BaseModel):
    """團隊通知請求"""
    project_id: int
    event_id: int
    custom_recipients: Optional[List[int]] = None


class ProjectUpdateRequest(BaseModel):
    """專案更新通知請求"""
    project_id: int
    update_content: str
    assignee_name: Optional[str] = "系統"
    exclude_user_ids: Optional[List[int]] = None


class SingleMarkReadRequest(BaseModel):
    """標記單一通知已讀請求"""
    notification_id: int


class NotificationResponse(BaseModel):
    """專案通知回應項目"""
    id: int
    title: str
    message: str
    notification_type: str
    priority: int
    is_read: bool
    created_at: datetime
    related_object_type: Optional[str] = None
    related_object_id: Optional[int] = None
    action_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 通用回應 Schema
# =============================================================================

class NotificationSuccessResponse(BaseModel):
    """通用成功回應"""
    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None
