# -*- coding: utf-8 -*-
"""IntegrationFacade - Integration context 對外唯一入口

v6.10 P1 Phase B（2026-05-18）

解 step 29 揭發最大宗跨 context 依賴：
  - integration -> ai (12 imports)  -- 此 facade 將被 ai/ 改 import
  - notification -> integration (9 imports)
  - memory -> integration (7 imports)
  - tender -> integration (2 imports)

統一封 LINE / Telegram / Discord 三 channel 操作 + admin push 模式。
"""
from __future__ import annotations

from typing import Any, Optional


class IntegrationFacade:
    """Integration bounded context 對外唯一入口

    封 LINE / Telegram / Discord 三 channel 的：
      - 主動推送 (push_admin / push_user)
      - 被動回覆 (reply_to_webhook)
      - channel 偵測 (detect_user_channel)

    使用範例：
        facade = IntegrationFacade()
        await facade.push_admin_alert(
            title="[ALERT] DB Pool",
            body="active=49/50",
        )
    """

    def __init__(self):
        pass

    # === Public API ===

    async def push_admin_alert(
        self,
        title: str,
        body: str,
        *,
        channel: Optional[str] = None,
    ) -> bool:
        """主動推送告警給 admin (多通道 fallback)

        取代 anti-pattern:
          from app.services.integration.line_bot import push_admin_alert
        """
        from app.services.contracts.adapters.messaging_default import DefaultMessagingAdapter
        msg = DefaultMessagingAdapter()
        return await msg.push_admin(title=title, body=body, channel=channel)

    async def push_to_user(
        self,
        user_channel_id: str,
        body: str,
        *,
        channel: str,
    ) -> bool:
        """主動推送到特定 user (LINE user_id / Telegram chat_id 等)"""
        from app.services.contracts.adapters.messaging_default import DefaultMessagingAdapter
        msg = DefaultMessagingAdapter()
        return await msg.reply_user(user_channel_id, body, channel=channel)

    async def send_morning_report(
        self,
        report_text: str,
        target_users: list[str],
        *,
        channel: str = "line",
    ) -> dict:
        """發送晨報到指定使用者群

        取代 anti-pattern (晨報多處重複 push 邏輯)
        """
        results: dict[str, bool] = {}
        for uid in target_users:
            ok = await self.push_to_user(uid, report_text, channel=channel)
            results[uid] = ok
        return {
            "total": len(target_users),
            "success": sum(1 for v in results.values() if v),
            "failed": sum(1 for v in results.values() if not v),
        }

    async def get_channel_for_user(self, user_id: int) -> Optional[str]:
        """偵測 user 偏好通道 (line / telegram / discord)

        取代 anti-pattern:
          from app.services.integration.channel_adapter import detect_channel
        """
        from app.services.integration.channel_adapter import detect_user_channel
        try:
            return await detect_user_channel(user_id)
        except (ImportError, AttributeError):
            return None

    async def get_sender_context(self, raw_request: Any) -> Optional[dict]:
        """從 webhook request 解析來源（LINE/Telegram/Discord）

        取代 ai/agent_orchestrator.py 直 import sender_context
        """
        try:
            from app.services.integration.sender_context import parse_sender_context
            return await parse_sender_context(raw_request)
        except (ImportError, AttributeError):
            return None


__all__ = ["IntegrationFacade"]
