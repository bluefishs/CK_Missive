"""
Pydantic schemas for Notifications
通知相關的統一 Schema 定義

包含：
- 系統通知 (System Notifications)
- 專案通知 (Project Notifications)
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
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


# =============================================================================
# 專案通知查詢 Schema (替代 dict 參數)
# =============================================================================

class BroadcastRequest(BaseModel):
    """專案團隊廣播請求"""
    title: str = Field(..., min_length=1, max_length=200, description="廣播標題")
    message: str = Field(..., min_length=1, max_length=2000, description="廣播內容")
    priority: int = Field(default=3, ge=1, le=5, description="優先級 (1-5)")


class UserNotificationsQuery(BaseModel):
    """使用者通知查詢請求"""
    unread_only: bool = Field(default=False, description="僅顯示未讀通知")
    limit: int = Field(default=50, ge=1, le=1000, description="回傳數量上限")


# ────────── 治理告警併入晨報（`POST /api/notify/digest`）──────────
#
# 2026-08-26：原本定義在 `api/endpoints/notify.py` 裡（08-21 補認證時新增），
# 違反 development-rules §3「endpoints 不得有本地 BaseModel」。純搬遷。
#
# 常數一併搬過來 —— 把 schema 搬走卻把它依賴的界限留在端點檔，
# 就變成「定義在這裡、約束在那裡」，改其中一邊不會有任何一方報錯。

MAX_TEXT_LEN = 800
MAX_TOPIC_LEN = 40
DEFAULT_TOPIC = "治理告警"


class DigestIn(BaseModel):
    """
    兩種都收：
      {"topic": "SSO 健康", "text": "..."}   明確指定主題
      {"text": "..."}                        Slack webhook 相容，主題用預設值
    """

    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LEN,
                      description="內容；超長請自行摘要，這裡不截斷而是拒收")
    topic: Optional[str] = Field(None, max_length=MAX_TOPIC_LEN,
                                 description="主題（會成為晨報裡的分段標題）")

    @model_validator(mode="after")
    def _fill_topic(self):
        # 空字串與 None 一律視為未指定 —— 空主題會讓晨報出現一個沒有標題的段落
        if not (self.topic or "").strip():
            self.topic = DEFAULT_TOPIC
        return self
