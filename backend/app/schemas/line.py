"""
LINE Bot Schemas

Version: 1.0.0
Created: 2026-03-15
"""

from pydantic import BaseModel, Field


class LinePushRequest(BaseModel):
    """Push 通知請求（內部系統使用）"""

    user_id: str = Field(..., min_length=1, max_length=64, description="LINE User ID")
    message: str = Field(..., min_length=1, max_length=5000, description="推播訊息內容")


class LinePushAlertsRequest(BaseModel):
    """警報推播請求"""

    target_user_ids: list[str] = Field(default=[], description="推播對象 LINE User ID (空=查詢 DB)")
    min_severity: str = Field(default="warning", description="最低推播嚴重度 (critical/warning/info)")


class LinePushAlertsResponse(BaseModel):
    """警報推播結果"""

    status: str = "ok"
    total_alerts: int = 0
    target_users: int = 0
    sent: int = 0
    failed: int = 0
    scanned: int = 0


class WebhookResponse(BaseModel):
    """LINE Webhook 回應"""
    status: str = "ok"
