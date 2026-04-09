"""
NemoClaw 夜間吹哨者排程任務 — 單元測試

測試 Phase 7-C: proactive_trigger_scan_job() 整合掃描 + 通知持久化 + LINE 推播

Version: 1.0.0
Created: 2026-03-22
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.proactive.proactive_triggers import TriggerAlert


def _make_alert(
    alert_type: str = "budget_overrun",
    severity: str = "warning",
    title: str = "test",
    message: str = "test msg",
    entity_type: str = "finance",
    entity_id: int = 1,
    metadata: dict = None,
) -> TriggerAlert:
    return TriggerAlert(
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
    )


class TestProactiveTriggerScanJob:
    """proactive_trigger_scan_job 排程任務測試"""

    @pytest.mark.asyncio
    async def test_scan_and_persist_warnings(self):
        """掃描結果中 warning+ 應持久化為通知"""
        mock_db = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_base = AsyncMock()
        mock_base.scan_all = AsyncMock(return_value=[
            _make_alert(alert_type="deadline_warning", severity="info", title="即將到期"),
            _make_alert(alert_type="deadline_overdue", severity="warning", title="已逾期"),
        ])

        mock_erp = AsyncMock()
        mock_erp.scan_all = AsyncMock(return_value=[
            _make_alert(severity="critical", title="預算超支 120%"),
            _make_alert(severity="warning", title="請款逾期 45 天"),
        ])

        mock_safe_notify = AsyncMock(return_value=True)

        mock_line_push = AsyncMock()
        mock_line_push.scan_and_push = AsyncMock(return_value={"sent": 0})

        with (
            patch("app.db.database.async_session_maker", return_value=mock_session_ctx),
            patch("app.services.ai.proactive.proactive_triggers.ProactiveTriggerService", return_value=mock_base),
            patch("app.services.ai.proactive.proactive_triggers_erp.ERPTriggerScanner", return_value=mock_erp),
            patch("app.services.notification_helpers._safe_create_notification", mock_safe_notify),
            patch("app.services.line_push_scheduler.LinePushScheduler", return_value=mock_line_push),
        ):
            from app.core.scheduler import proactive_trigger_scan_job
            await proactive_trigger_scan_job()

        # 應持久化 3 筆 (1 base warning + 1 critical + 1 warning)
        assert mock_safe_notify.call_count == 3

        # 驗證 critical alert 存在
        critical_calls = [c for c in mock_safe_notify.call_args_list if "critical" in str(c)]
        assert len(critical_calls) >= 1

    @pytest.mark.asyncio
    async def test_info_alerts_not_persisted(self):
        """info 級別警報不應持久化"""
        mock_db = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_base = AsyncMock()
        mock_base.scan_all = AsyncMock(return_value=[
            _make_alert(severity="info", title="低優先通知"),
        ])
        mock_erp = AsyncMock()
        mock_erp.scan_all = AsyncMock(return_value=[
            _make_alert(severity="info", title="即將到期"),
        ])
        mock_safe_notify = AsyncMock(return_value=True)
        mock_line_push = AsyncMock()
        mock_line_push.scan_and_push = AsyncMock(return_value={"sent": 0})

        with (
            patch("app.db.database.async_session_maker", return_value=mock_session_ctx),
            patch("app.services.ai.proactive.proactive_triggers.ProactiveTriggerService", return_value=mock_base),
            patch("app.services.ai.proactive.proactive_triggers_erp.ERPTriggerScanner", return_value=mock_erp),
            patch("app.services.notification_helpers._safe_create_notification", mock_safe_notify),
            patch("app.services.line_push_scheduler.LinePushScheduler", return_value=mock_line_push),
        ):
            from app.core.scheduler import proactive_trigger_scan_job
            await proactive_trigger_scan_job()

        mock_safe_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_line_push_failure_does_not_break_job(self):
        """LINE 推播失敗不應中斷主流程"""
        mock_db = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_base = AsyncMock()
        mock_base.scan_all = AsyncMock(return_value=[])
        mock_erp = AsyncMock()
        mock_erp.scan_all = AsyncMock(return_value=[
            _make_alert(severity="warning", title="test"),
        ])
        mock_safe_notify = AsyncMock(return_value=True)

        mock_line_push = AsyncMock()
        mock_line_push.scan_and_push = AsyncMock(side_effect=Exception("LINE API 異常"))

        with (
            patch("app.db.database.async_session_maker", return_value=mock_session_ctx),
            patch("app.services.ai.proactive.proactive_triggers.ProactiveTriggerService", return_value=mock_base),
            patch("app.services.ai.proactive.proactive_triggers_erp.ERPTriggerScanner", return_value=mock_erp),
            patch("app.services.notification_helpers._safe_create_notification", mock_safe_notify),
            patch("app.services.line_push_scheduler.LinePushScheduler", return_value=mock_line_push),
        ):
            from app.core.scheduler import proactive_trigger_scan_job
            # 不應拋出異常
            await proactive_trigger_scan_job()

        # 通知仍應被持久化
        assert mock_safe_notify.call_count == 1

    @pytest.mark.asyncio
    async def test_scanner_exception_caught(self):
        """掃描器異常應被 catch 不影響服務"""
        mock_db = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_base = AsyncMock()
        mock_base.scan_all = AsyncMock(side_effect=Exception("DB connection error"))

        mock_safe_notify = AsyncMock(return_value=True)

        with (
            patch("app.db.database.async_session_maker", return_value=mock_session_ctx),
            patch("app.services.ai.proactive.proactive_triggers.ProactiveTriggerService", return_value=mock_base),
            patch("app.services.ai.proactive.proactive_triggers_erp.ERPTriggerScanner"),
            patch("app.services.notification_helpers._safe_create_notification", mock_safe_notify),
        ):
            from app.core.scheduler import proactive_trigger_scan_job
            # 不應拋出異常
            await proactive_trigger_scan_job()

        # notify 不應被呼叫 (異常在掃描階段)
        mock_safe_notify.assert_not_called()


class TestSetupSchedulerRegistration:
    """驗證 setup_scheduler 正確註冊夜間吹哨者"""

    def test_proactive_scan_job_registered(self):
        """setup_scheduler 應包含 proactive_trigger_scan 任務"""
        from app.core.scheduler import setup_scheduler

        scheduler = setup_scheduler()
        job_ids = [job.id for job in scheduler.get_jobs()]

        assert "proactive_trigger_scan" in job_ids

    def test_proactive_scan_job_schedule(self):
        """夜間吹哨者應排在 00:30"""
        from app.core.scheduler import setup_scheduler

        scheduler = setup_scheduler()
        job = next(j for j in scheduler.get_jobs() if j.id == "proactive_trigger_scan")

        # CronTrigger 的 fields 檢查
        trigger_str = str(job.trigger)
        assert "0" in trigger_str  # hour=0
        assert "30" in trigger_str  # minute=30


class TestLinePushTypeLabels:
    """驗證 LinePushScheduler 類型標籤完整性"""

    def test_budget_overrun_label_exists(self):
        from app.services.line_push_scheduler import LinePushScheduler
        assert "budget_overrun" in LinePushScheduler._TYPE_LABELS
        assert LinePushScheduler._TYPE_LABELS["budget_overrun"] == "預算警報"

    def test_pending_receipt_label_exists(self):
        from app.services.line_push_scheduler import LinePushScheduler
        assert "pending_receipt_stale" in LinePushScheduler._TYPE_LABELS
        assert LinePushScheduler._TYPE_LABELS["pending_receipt_stale"] == "待核銷提醒"
