# -*- coding: utf-8 -*-
"""MessagingPort 預設實作 — 多通道 fallback（LINE / Telegram / Discord）

v6.10 P1 建議 1 配套（2026-05-18）

取代散落於 autobiography.py (687L) / scheduler.py / agent_critic.py 等 module 的
跨打三 channel 反模式。新 service 走 MessagingPort.push_admin()，多通道自動 fallback。

L51 (2026-05-29) 補丁:
- _get_admin_id 缺失升 warning + metric（防 silent fail 反覆）
- _push_one 對每次 attempt 記 Prometheus counter (channel, result)
"""
from __future__ import annotations

import logging
from typing import Optional

from app.services.contracts.ports.messaging import MessagingPort

logger = logging.getLogger(__name__)


# L51 (2026-05-29) messaging Prometheus counter — 失敗率監控基礎
try:
    from prometheus_client import Counter as _PromCounter, REGISTRY as _PROM_REG

    try:
        MESSAGING_PUSH_TOTAL = _PromCounter(
            "messaging_push_total",
            "Messaging push attempts by channel and result (L51 silent-fail prevention)",
            ["channel", "result"],  # channel: line/telegram/discord
                                    # result: success/missing_admin_id/service_unavailable/exception/disabled
            registry=_PROM_REG,
        )
        # 預宣告全 label 組合，讓 /metrics 永遠輸出 sample（即使從未 inc 也算「真活」）
        for ch in ("line", "telegram", "discord"):
            for r in ("success", "missing_admin_id", "service_unavailable",
                      "exception", "disabled"):
                MESSAGING_PUSH_TOTAL.labels(channel=ch, result=r).inc(0)
    except ValueError:
        # 已註冊（多次 import）→ 從 REGISTRY 重用
        MESSAGING_PUSH_TOTAL = None
        for collector in list(_PROM_REG._names_to_collectors.values()):
            if getattr(collector, "_name", None) == "messaging_push":
                MESSAGING_PUSH_TOTAL = collector
                break
except Exception:
    MESSAGING_PUSH_TOTAL = None


def _track_push(channel: str, result: str) -> None:
    """failure-safe metric inc — 任何 metric 失敗都不擋業務"""
    if MESSAGING_PUSH_TOTAL is None:
        return
    try:
        MESSAGING_PUSH_TOTAL.labels(channel=channel, result=result).inc()
    except Exception:
        pass


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
        """單通道推送（含 admin push 預設 target = 環境變數中的 admin id）

        L51: 每次 attempt 計數到 Prometheus + silent fail 升 warning log
        """
        if channel == "line":
            from app.services.integration.line_bot import get_line_bot_service
            svc = get_line_bot_service()
            if not svc:
                logger.warning(
                    "[Messaging] LINE service unavailable (get_line_bot_service returned None)"
                )
                _track_push("line", "service_unavailable")
                return False
            admin_id = target or self._get_admin_id("LINE_ADMIN_USER_ID")
            if not admin_id:
                _track_push("line", "missing_admin_id")
                return False
            ok = await svc.push_message(admin_id, text)
            _track_push("line", "success" if ok else "exception")
            return ok

        if channel == "telegram":
            # ADR-0027：Telegram 5/4 永封後 admin push 預設關閉
            import os
            if os.getenv("TELEGRAM_ADMIN_PUSH_ENABLED", "false").lower() != "true":
                _track_push("telegram", "disabled")
                return False
            from app.services.integration.telegram_bot import get_telegram_bot_service
            svc = get_telegram_bot_service()
            if not svc:
                logger.warning("[Messaging] Telegram service unavailable")
                _track_push("telegram", "service_unavailable")
                return False
            admin_id = target or self._get_admin_id("TELEGRAM_ADMIN_CHAT_ID")
            if not admin_id:
                _track_push("telegram", "missing_admin_id")
                return False
            ok = await svc.send_message(admin_id, text)
            _track_push("telegram", "success" if ok else "exception")
            return ok

        if channel == "discord":
            # Discord 主要被動回覆，不主動 admin push
            if not target:
                _track_push("discord", "missing_admin_id")
                return False
            try:
                from app.services.integration.discord_bot import send_discord_message
                ok = await send_discord_message(target, text)
                _track_push("discord", "success" if ok else "exception")
                return ok
            except (ImportError, AttributeError):
                _track_push("discord", "service_unavailable")
                return False

        logger.warning("Unknown messaging channel: %s", channel)
        return False

    @staticmethod
    def _get_admin_id(env_key: str) -> Optional[str]:
        """L51 升級：silent fail (return None) 改 warning log，可被觀測

        過去 silent return None 是 L51 LINE 事故根因之一。
        現在缺失即 warn — 容易在 docker logs 中發現 root cause。
        """
        import os
        val = os.getenv(env_key)
        if not val:
            logger.warning(
                "[Messaging] admin_id env %r missing — channel push will skip "
                "(check docker-compose env injection)", env_key,
            )
        return val


__all__ = ["DefaultMessagingAdapter"]
