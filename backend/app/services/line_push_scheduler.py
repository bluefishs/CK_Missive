"""
LINE 推播排程器 — 定時掃描 ProactiveAlerts 並推播 LINE 通知

整合：
- ProactiveTriggerService: 掃描截止日/逾期/品質警報
- LineBotService: 推播 LINE 訊息

排程模式：
- 手動觸發: POST /line/push-alerts
- 背景排程: 可由 APScheduler / cron job 定期呼叫

Version: 1.0.0
Created: 2026-03-15
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.proactive_triggers import ProactiveTriggerService, TriggerAlert
from app.services.line_bot_service import get_line_bot_service

logger = logging.getLogger(__name__)


class LinePushScheduler:
    """LINE 推播排程器"""

    # 嚴重度對應 emoji
    _SEVERITY_EMOJI = {
        "critical": "🔴",
        "warning": "🟡",
        "info": "🔵",
    }

    # 類型對應中文標籤
    _TYPE_LABELS = {
        "deadline_overdue": "逾期提醒",
        "deadline_warning": "截止提醒",
        "data_quality": "資料品質",
        "payment_overdue": "請款逾期",
        "payment_warning": "請款提醒",
        "invoice_reminder": "發票催開",
        "vendor_payment_overdue": "外包付款逾期",
        "vendor_payment_warning": "外包付款提醒",
        "budget_overrun": "預算警報",
        "pending_receipt_stale": "待核銷提醒",
        "recommendation": "智慧推薦",
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self._trigger_service = ProactiveTriggerService(db)
        self._line_service = get_line_bot_service()

    async def scan_and_push(
        self,
        target_user_ids: Optional[List[str]] = None,
        min_severity: str = "warning",
    ) -> Dict[str, Any]:
        """
        掃描警報並推播給指定使用者。

        Args:
            target_user_ids: 推播對象 LINE User ID 列表。
                若未提供，從 DB 查詢有 line_user_id 的使用者。
            min_severity: 最低推播嚴重度 (critical/warning/info)

        Returns:
            推播結果摘要
        """
        if not self._line_service.enabled:
            return {"status": "disabled", "sent": 0}

        # 掃描警報
        alerts = await self._trigger_service.scan_all()

        # 篩選嚴重度
        severity_order = {"critical": 3, "warning": 2, "info": 1}
        min_level = severity_order.get(min_severity, 2)
        filtered = [
            a for a in alerts
            if severity_order.get(a.severity, 0) >= min_level
        ]

        if not filtered:
            return {"status": "no_alerts", "scanned": len(alerts), "sent": 0}

        # 取得推播對象
        user_ids = target_user_ids or await self._get_push_targets()

        if not user_ids:
            return {"status": "no_targets", "alerts": len(filtered), "sent": 0}

        # 組合訊息
        message = self._format_alerts(filtered)

        # 逐一推播
        sent_count = 0
        failed_count = 0

        for uid in user_ids:
            success = await self._line_service.push_message(uid, message)
            if success:
                sent_count += 1
            else:
                failed_count += 1

        result = {
            "status": "sent",
            "total_alerts": len(filtered),
            "target_users": len(user_ids),
            "sent": sent_count,
            "failed": failed_count,
        }

        logger.info(
            "LINE push scheduler: %d alerts → %d/%d users",
            len(filtered),
            sent_count,
            len(user_ids),
        )

        return result

    async def _get_push_targets(self) -> List[str]:
        """
        從 DB 查詢啟用 LINE 通知的使用者。

        查詢 User 表的 line_user_id 欄位（若已建立）。
        若欄位不存在，回傳空列表。
        """
        try:
            from sqlalchemy import select, text
            from app.extended.models.core import User

            # 檢查 line_user_id 欄位是否存在
            if not hasattr(User, "line_user_id"):
                return []

            result = await self.db.execute(
                select(User.line_user_id).where(
                    User.line_user_id.isnot(None),
                    User.line_user_id != "",
                )
            )
            return [row[0] for row in result.all()]

        except Exception as e:
            logger.debug("Failed to get push targets: %s", e)
            return []

    def _format_alerts(self, alerts: List[TriggerAlert]) -> str:
        """將警報格式化為 LINE 訊息文字"""
        lines = ["📋 系統警報通知\n"]

        # 摘要統計
        critical = sum(1 for a in alerts if a.severity == "critical")
        warning = sum(1 for a in alerts if a.severity == "warning")
        if critical:
            lines.append(f"🔴 緊急: {critical} 項")
        if warning:
            lines.append(f"🟡 警告: {warning} 項")
        lines.append("")

        # 各項警報（最多 10 項）
        for alert in alerts[:10]:
            emoji = self._SEVERITY_EMOJI.get(alert.severity, "⚪")
            type_label = self._TYPE_LABELS.get(alert.alert_type, alert.alert_type)
            lines.append(f"{emoji} [{type_label}] {alert.title}")
            lines.append(f"   {alert.message}")
            lines.append("")

        if len(alerts) > 10:
            lines.append(f"...另有 {len(alerts) - 10} 項警報")

        message = "\n".join(lines)

        # LINE 上限 5000 字
        if len(message) > 5000:
            message = message[:4990] + "\n...(已截斷)"

        return message
