# -*- coding: utf-8 -*-
"""MessagingPort — 統一 LINE / Telegram / Discord 通訊 facade（v6.10 P1 建議 1）

替代目前散落於 services/integration/{line_bot,telegram_bot,discord_bot}.py
+ services/memory/autobiography.py (687L) 多 channel 跨打模式。

外部呼叫者只透過此 Port，不直接 import 任一 channel module。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class MessagingPort(ABC):
    """跨通道訊息 facade

    替代 anti-pattern：
      ❌  from app.services.integration.line_bot import push_admin_alert
      ✅  from app.services.contracts import MessagingPort
          msg.push_admin(title, body)
    """

    @abstractmethod
    async def push_admin(
        self,
        title: str,
        body: str,
        *,
        channel: Optional[str] = None,  # "line" / "telegram" / "discord" / None=default
    ) -> bool:
        """主動推送告警給 admin（多通道 fallback）"""
        raise NotImplementedError

    @abstractmethod
    async def reply_user(
        self,
        user_channel_id: str,
        body: str,
        *,
        channel: str,
    ) -> bool:
        """回覆使用者（被動 webhook 觸發後）"""
        raise NotImplementedError


__all__ = ["MessagingPort"]
