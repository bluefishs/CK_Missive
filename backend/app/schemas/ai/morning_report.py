"""晨報訂閱（2026-08-17 由 `api/endpoints/ai/morning_report_subscriptions.py` 搬入）

依 `.claude/rules/development-rules.md` §3。
"""
from typing import Optional

from pydantic import BaseModel, Field



class SubscriptionCreateRequest(BaseModel):
    channel: str = Field(..., description="telegram/line/discord/email")
    channel_recipient: str = Field(..., description="chat_id / user_id / email")
    display_name: Optional[str] = Field(None)
    sections: Optional[str] = Field("dispatch,meeting,site_visit,missing")
    handler_filter: Optional[str] = Field(None)
    user_id: Optional[int] = Field(None)


class SubscriptionUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    sections: Optional[str] = None
    handler_filter: Optional[str] = None
    enabled: Optional[bool] = None
