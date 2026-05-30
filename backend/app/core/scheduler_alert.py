# -*- coding: utf-8 -*-
"""
排程器失敗告警管理器

在排程任務連續失敗達閾值時，透過 Telegram 推播告警。
內建冷卻機制避免告警風暴。

Usage:
    在 tracked_job 的 except 分支中呼叫：
        await alert_manager.send_failure_alert(job_id, str(e), failure_count)
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def get_telegram_bot_service():
    """Lazy import to avoid circular dependencies."""
    from app.services.integration.telegram_bot import get_telegram_bot_service as _get
    return _get()


class SchedulerAlertManager:
    """管理排程器失敗告警的閾值、冷卻與發送。"""

    def __init__(
        self,
        failure_threshold: int = 2,
        cooldown_seconds: int = 300,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._last_alert_time: Dict[str, datetime] = {}

    def format_alert(self, job_id: str, error: str, failure_count: int) -> str:
        """格式化告警訊息"""
        return (
            f"🚨 排程任務失敗告警\n\n"
            f"任務: {job_id}\n"
            f"連續失敗: {failure_count} 次\n"
            f"錯誤: {error[:300]}\n"
            f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def should_alert(self, job_id: str, failure_count: int) -> bool:
        """判斷是否應該發送告警"""
        if failure_count < self.failure_threshold:
            return False

        last = self._last_alert_time.get(job_id)
        if last and (datetime.now() - last).total_seconds() < self.cooldown_seconds:
            return False

        return True

    def record_alert_sent(self, job_id: str):
        """記錄告警已發送時間"""
        self._last_alert_time[job_id] = datetime.now()

    async def send_failure_alert(
        self,
        job_id: str,
        error: str,
        failure_count: int,
    ) -> bool:
        """發送失敗告警 (v6.12 B 方案 2026-05-30: 改走 IntegrationFacade 多通道 fallback)

        前: Telegram only → TELEGRAM_ADMIN_CHAT_ID 沒設就 silent skip
        後: IntegrationFacade.push_admin_alert → LINE / Telegram 任一可用就送
        """
        title = f"⚠️ 排程失敗 {job_id}"
        body = self.format_alert(job_id, error, failure_count)

        try:
            # v6.12 B 方案: caller +1 facade trial 推進
            from app.services.contracts.facades.integration import IntegrationFacade
            ok = await IntegrationFacade().push_admin_alert(title=title, body=body)
            if ok:
                self.record_alert_sent(job_id)
                logger.info("排程失敗告警已發送 (多通道): job=%s, failures=%d", job_id, failure_count)
                return True
            logger.warning("排程失敗告警 push_admin_alert 回 False (無可用通道)")
            return False
        except Exception as e:
            logger.warning("排程失敗告警發送失敗: %s", e)
            return False


# 全域單例
_alert_manager: Optional[SchedulerAlertManager] = None


def get_alert_manager() -> SchedulerAlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = SchedulerAlertManager()
    return _alert_manager
