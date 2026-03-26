"""
統一通知派發器 — LINE / Discord 多通道推送

集中管理所有主動推送：截止日提醒、預算警報、系統異常等。
各通道自動適配格式（LINE Flex / Discord Embed / 純文字回退）。

Usage:
    dispatcher = NotificationDispatcher()
    await dispatcher.send_deadline_alert(user, doc_subject, deadline)
    await dispatcher.send_budget_alert(user, project_name, amount)
    await dispatcher.broadcast_system_alert(message, severity)

Version: 1.0.0
Created: 2026-03-25
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    LINE = "line"
    DISCORD = "discord"
    ALL = "all"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class NotificationTarget:
    """通知對象"""
    user_id: int                        # 系統 User ID
    line_user_id: Optional[str] = None  # LINE User ID
    discord_channel_id: Optional[str] = None  # Discord Channel ID
    preferred_channel: NotificationChannel = NotificationChannel.ALL


class NotificationDispatcher:
    """多通道通知派發器"""

    async def send_deadline_alert(
        self,
        target: NotificationTarget,
        doc_subject: str,
        deadline: str,
    ) -> Dict[str, bool]:
        """推送公文截止提醒"""
        results = {}

        if target.line_user_id and target.preferred_channel in (
            NotificationChannel.LINE, NotificationChannel.ALL,
        ):
            results["line"] = await self._push_line_deadline(
                target.line_user_id, doc_subject, deadline,
            )

        if target.discord_channel_id and target.preferred_channel in (
            NotificationChannel.DISCORD, NotificationChannel.ALL,
        ):
            results["discord"] = await self._push_discord_deadline(
                target.discord_channel_id, doc_subject, deadline,
            )

        return results

    async def send_budget_alert(
        self,
        target: NotificationTarget,
        project_name: str,
        budget_used_percent: float,
        amount: float,
    ) -> Dict[str, bool]:
        """推送預算超支警報"""
        message = (
            f"⚠️ 預算警報\n\n"
            f"專案：{project_name}\n"
            f"使用率：{budget_used_percent:.1f}%\n"
            f"已支出：{amount:,.0f} 元"
        )
        return await self._broadcast(target, message, Severity.WARNING)

    async def send_system_alert(
        self,
        target: NotificationTarget,
        message: str,
        severity: Severity = Severity.WARNING,
    ) -> Dict[str, bool]:
        """推送系統警報"""
        prefix = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(severity, "⚠️")
        return await self._broadcast(target, f"{prefix} {message}", severity)

    async def broadcast_to_all(
        self,
        message: str,
        severity: Severity = Severity.INFO,
        line_user_ids: List[str] = None,
        discord_channel_ids: List[str] = None,
    ) -> Dict[str, int]:
        """廣播通知到所有通道"""
        sent = {"line": 0, "discord": 0}

        if line_user_ids:
            from app.services.line_bot_service import get_line_bot_service
            service = get_line_bot_service()
            for uid in line_user_ids:
                if await service.push_message(uid, message):
                    sent["line"] += 1

        if discord_channel_ids:
            from app.services.discord_bot_service import get_discord_bot_service
            service = get_discord_bot_service()
            for cid in discord_channel_ids:
                if await service.send_channel_message(cid, message):
                    sent["discord"] += 1

        return sent

    # ── 私有方法 ──

    async def _push_line_deadline(
        self, line_user_id: str, doc_subject: str, deadline: str,
    ) -> bool:
        try:
            from app.services.line_bot_service import get_line_bot_service
            service = get_line_bot_service()
            return await service.push_deadline_reminder(line_user_id, doc_subject, deadline)
        except Exception as e:
            logger.error("LINE deadline push failed: %s", e)
            return False

    async def _push_discord_deadline(
        self, channel_id: str, doc_subject: str, deadline: str,
    ) -> bool:
        try:
            from app.services.discord_bot_service import get_discord_bot_service
            service = get_discord_bot_service()
            message = f"📋 **公文截止提醒**\n主旨：{doc_subject}\n截止日：{deadline}"
            return await service.send_channel_message(channel_id, message)
        except Exception as e:
            logger.error("Discord deadline push failed: %s", e)
            return False

    async def _broadcast(
        self, target: NotificationTarget, message: str, severity: Severity,
    ) -> Dict[str, bool]:
        results = {}

        if target.line_user_id and target.preferred_channel in (
            NotificationChannel.LINE, NotificationChannel.ALL,
        ):
            try:
                from app.services.line_bot_service import get_line_bot_service
                results["line"] = await get_line_bot_service().push_message(
                    target.line_user_id, message,
                )
            except Exception as e:
                logger.error("LINE broadcast failed: %s", e)
                results["line"] = False

        if target.discord_channel_id and target.preferred_channel in (
            NotificationChannel.DISCORD, NotificationChannel.ALL,
        ):
            try:
                from app.services.discord_bot_service import get_discord_bot_service
                results["discord"] = await get_discord_bot_service().send_channel_message(
                    target.discord_channel_id, message,
                )
            except Exception as e:
                logger.error("Discord broadcast failed: %s", e)
                results["discord"] = False

        return results
