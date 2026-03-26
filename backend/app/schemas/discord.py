"""
Discord Bot Schemas

Version: 1.0.0
Created: 2026-03-25
"""

from pydantic import BaseModel, Field


class DiscordPushRequest(BaseModel):
    """Push 通知請求（內部系統使用）"""

    channel_id: str = Field(..., min_length=1, max_length=64, description="Discord Channel ID")
    message: str = Field(..., min_length=1, max_length=2000, description="推播訊息內容")


class DiscordWebhookResponse(BaseModel):
    """Discord Webhook 回應"""
    type: int = 1  # PONG
