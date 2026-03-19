"""
LINE Push Scheduler 單元測試

Version: 1.0.0
Created: 2026-03-15
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.proactive_triggers import TriggerAlert


# ── Test Data ──

MOCK_ALERTS = [
    TriggerAlert(
        alert_type="deadline_overdue",
        severity="critical",
        title="事件已逾期 3 天",
        message="「重要公文」已逾期 3 天",
        entity_type="document",
        entity_id=1,
    ),
    TriggerAlert(
        alert_type="deadline_warning",
        severity="warning",
        title="事件將於 2 天內到期",
        message="「緊急案件」將於 2 天內到期",
        entity_type="project",
        entity_id=2,
    ),
    TriggerAlert(
        alert_type="data_quality",
        severity="info",
        title="5 筆公文缺少主旨",
        message="有 5 筆公文沒有主旨",
        entity_type="system",
    ),
]


# ── Tests ──


class TestLinePushScheduler:
    """推播排程器核心測試"""

    def _create_scheduler(self, line_enabled=True, alerts=None):
        mock_db = AsyncMock()

        with patch("app.services.line_push_scheduler.ProactiveTriggerService") as mock_trigger, \
             patch("app.services.line_push_scheduler.get_line_bot_service") as mock_line_fn:

            mock_trigger_instance = AsyncMock()
            mock_trigger_instance.scan_all = AsyncMock(return_value=alerts or [])
            mock_trigger.return_value = mock_trigger_instance

            mock_line = MagicMock()
            mock_line.enabled = line_enabled
            mock_line.push_message = AsyncMock(return_value=True)
            mock_line_fn.return_value = mock_line

            from app.services.line_push_scheduler import LinePushScheduler
            scheduler = LinePushScheduler(mock_db)
            return scheduler, mock_line, mock_trigger_instance

    @pytest.mark.asyncio
    async def test_disabled_returns_immediately(self):
        scheduler, mock_line, _ = self._create_scheduler(line_enabled=False)
        result = await scheduler.scan_and_push(target_user_ids=["U123"])
        assert result["status"] == "disabled"
        assert result["sent"] == 0

    @pytest.mark.asyncio
    async def test_no_alerts_skips_push(self):
        scheduler, mock_line, _ = self._create_scheduler(alerts=[])
        result = await scheduler.scan_and_push(target_user_ids=["U123"])
        assert result["status"] == "no_alerts"
        mock_line.push_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_targets_skips_push(self):
        scheduler, mock_line, _ = self._create_scheduler(alerts=MOCK_ALERTS)
        # Mock _get_push_targets returns empty
        scheduler._get_push_targets = AsyncMock(return_value=[])
        result = await scheduler.scan_and_push()
        assert result["status"] == "no_targets"
        mock_line.push_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_to_specified_users(self):
        scheduler, mock_line, _ = self._create_scheduler(alerts=MOCK_ALERTS)

        result = await scheduler.scan_and_push(
            target_user_ids=["U001", "U002"],
            min_severity="warning",
        )

        assert result["status"] == "sent"
        assert result["sent"] == 2
        assert result["target_users"] == 2
        # info alerts filtered out
        assert result["total_alerts"] == 2  # only critical + warning
        assert mock_line.push_message.call_count == 2

    @pytest.mark.asyncio
    async def test_min_severity_filter(self):
        scheduler, mock_line, _ = self._create_scheduler(alerts=MOCK_ALERTS)

        result = await scheduler.scan_and_push(
            target_user_ids=["U001"],
            min_severity="critical",
        )

        assert result["total_alerts"] == 1  # only critical
        assert mock_line.push_message.call_count == 1

    @pytest.mark.asyncio
    async def test_all_severity_levels(self):
        scheduler, mock_line, _ = self._create_scheduler(alerts=MOCK_ALERTS)

        result = await scheduler.scan_and_push(
            target_user_ids=["U001"],
            min_severity="info",
        )

        assert result["total_alerts"] == 3  # all alerts

    @pytest.mark.asyncio
    async def test_push_failure_tracked(self):
        scheduler, mock_line, _ = self._create_scheduler(alerts=MOCK_ALERTS)
        # First push succeeds, second fails
        mock_line.push_message = AsyncMock(side_effect=[True, False])

        result = await scheduler.scan_and_push(
            target_user_ids=["U001", "U002"],
            min_severity="warning",
        )

        assert result["sent"] == 1
        assert result["failed"] == 1


class TestFormatAlerts:
    """訊息格式化測試"""

    def _create_scheduler(self):
        mock_db = AsyncMock()
        with patch("app.services.line_push_scheduler.ProactiveTriggerService"), \
             patch("app.services.line_push_scheduler.get_line_bot_service"):
            from app.services.line_push_scheduler import LinePushScheduler
            return LinePushScheduler(mock_db)

    def test_format_includes_header(self):
        scheduler = self._create_scheduler()
        message = scheduler._format_alerts(MOCK_ALERTS)
        assert "系統警報通知" in message

    def test_format_includes_severity_summary(self):
        scheduler = self._create_scheduler()
        message = scheduler._format_alerts(MOCK_ALERTS)
        assert "🔴" in message
        assert "🟡" in message

    def test_format_includes_alert_details(self):
        scheduler = self._create_scheduler()
        message = scheduler._format_alerts(MOCK_ALERTS)
        assert "逾期提醒" in message
        assert "截止提醒" in message
        assert "重要公文" in message

    def test_format_truncates_long_message(self):
        scheduler = self._create_scheduler()
        # Create many alerts
        many_alerts = [
            TriggerAlert(
                alert_type="deadline_overdue",
                severity="critical",
                title=f"Alert {i}" * 50,
                message=f"Detail {i}" * 100,
                entity_type="document",
            )
            for i in range(100)
        ]
        message = scheduler._format_alerts(many_alerts)
        assert len(message) <= 5000

    def test_format_limits_to_10_alerts(self):
        scheduler = self._create_scheduler()
        many_alerts = [
            TriggerAlert(
                alert_type="deadline_warning",
                severity="warning",
                title=f"Alert {i}",
                message=f"Detail {i}",
                entity_type="document",
            )
            for i in range(20)
        ]
        message = scheduler._format_alerts(many_alerts)
        assert "另有 10 項警報" in message
