# -*- coding: utf-8 -*-
"""MessagingPort 預設實作 — 多通道 fallback（LINE / Telegram / Discord）

v6.10 P1 建議 1 配套（2026-05-18）

取代散落於 autobiography.py (687L) / scheduler.py / agent_critic.py 等 module 的
跨打三 channel 反模式。新 service 走 MessagingPort.push_admin()，多通道自動 fallback。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.services.contracts.ports.messaging import MessagingPort

logger = logging.getLogger(__name__)


class DefaultMessagingAdapter(MessagingPort):
    """預設 messaging adapter — LINE 優先，Telegram fallback

    LINE 是 ADR-0027 後的 admin push 主通道（Telegram 5/4 永封後降為被動備援）。

    使用方式：
        msg = DefaultMessagingAdapter()
        await msg.push_admin("[ALERT] DB Pool", "active=49/50, queue full")
    """

    DEFAULT_CHANNEL_ORDER = ["line", "telegram", "discord"]

    async def push_admin(
        self,
        title: str,
        body: str,
        *,
        channel: Optional[str] = None,
    ) -> bool:
        """主動推送告警給 admin

        策略：
        - channel 指定：只試該 channel
        - 預設：依 DEFAULT_CHANNEL_ORDER 嘗試（含 ADR-0027 後 LINE 優先）
        """
        text = f"{title}\n\n{body}" if title else body
        channels = [channel] if channel else self.DEFAULT_CHANNEL_ORDER
        for ch in channels:
            try:
                if await self._push_one(ch, text):
                    return True
            except Exception as e:
                logger.warning("Messaging push via %s failed: %s", ch, e)
        logger.error("Messaging push 全 channel 失敗: %s", title)
        return False

    async def reply_user(
        self,
        user_channel_id: str,
        body: str,
        *,
        channel: str,
    ) -> bool:
        """回覆使用者（被動 webhook 觸發後）

        必須指定 channel — 因為 webhook 知道來源 channel。
        """
        try:
            return await self._push_one(channel, body, target=user_channel_id)
        except Exception as e:
            logger.error("Messaging reply via %s failed: %s", channel, e)
            return False

    async def _push_one(
        self, channel: str, text: str, *, target: Optional[str] = None,
    ) -> bool:
        """單通道推送（含 admin push 預設 target = 環境變數中的 admin id）"""
        if channel == "line":
            from app.services.integration.line_bot import get_line_bot_service
            svc = get_line_bot_service()
            if not svc:
                return False
            admin_id = target or self._get_admin_id("LINE_ADMIN_USER_ID")
            if not admin_id:
                return False
            return await svc.push_message(admin_id, text)

        if channel == "telegram":
            # ADR-0027：Telegram 5/4 永封後 admin push 預設關閉
            import os
            if os.getenv("TELEGRAM_ADMIN_PUSH_ENABLED", "false").lower() != "true":
                return False
            from app.services.integration.telegram_bot import get_telegram_bot_service
            svc = get_telegram_bot_service()
            if not svc:
                return False
            admin_id = target or self._get_admin_id("TELEGRAM_ADMIN_CHAT_ID")
            if not admin_id:
                return False
            return await svc.send_message(admin_id, text)

        if channel == "discord":
            # Discord 主要被動回覆，不主動 admin push
            if not target:
                return False
            try:
                from app.services.integration.discord_bot import send_discord_message
                return await send_discord_message(target, text)
            except (ImportError, AttributeError):
                return False

        logger.warning("Unknown messaging channel: %s", channel)
        return False

    @staticmethod
    def _get_admin_id(env_key: str) -> Optional[str]:
        import os
        return os.getenv(env_key)


__all__ = ["DefaultMessagingAdapter"]
