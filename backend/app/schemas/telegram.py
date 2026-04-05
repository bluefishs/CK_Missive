"""
Telegram Bot Schemas

Version: 1.0.0
Created: 2026-04-05
"""

from pydantic import BaseModel, Field


class TelegramPushRequest(BaseModel):
    """Push 通知請求（內部系統使用）"""

    chat_id: int = Field(..., description="Telegram Chat ID")
    message: str = Field(..., min_length=1, max_length=4096, description="推播訊息內容")


class TelegramWebhookResponse(BaseModel):
    """Telegram Webhook 回應"""
    status: str = "ok"
