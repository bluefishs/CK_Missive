"""
Proactive Triggers 單元測試

Version: 1.0.0
Created: 2026-03-15
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.proactive_triggers import (
    ProactiveTriggerService,
    TriggerAlert,
)
from app.services.ai.proactive_triggers_erp import ERPTriggerScanner


class TestTriggerAlert:
    """TriggerAlert 資料結構測試"""

    def test_create_alert(self):
        alert = TriggerAlert(
            alert_type="deadline_warning",
            severity="warning",
            title="test",
            message="test msg",
            entity_type="document",
            entity_id=1,
        )
        assert alert.alert_type == "deadline_warning"
        assert alert.metadata == {}

    def test_create_alert_with_metadata(self):
        alert = TriggerAlert(
            alert_type="deadline_overdue",
            severity="critical",
            title="逾期",
            message="逾期3天",
            entity_type="project",
            metadata={"days_overdue": 3},
        )
        assert alert.metadata["days_overdue"] == 3


class TestCheckDocumentDeadlines:
    """行事曆事件截止日檢查測試"""

    @pytest.mark.asyncio
    async def test_overdue_events(self):
        db = AsyncMock()

        past_date = date.today() - timedelta(days=3)
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.title = "重要公文截止"
        mock_row.end_date = past_date  # date object (not datetime)
        mock_row.document_id = 10

        overdue_result = MagicMock()
        overdue_result.all.return_value = [mock_row]

        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ProactiveTriggerService(db)
        alerts = await svc.check_document_deadlines()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "deadline_overdue"
        assert alerts[0].severity == "critical"
        assert "3" in alerts[0].title

    @pytest.mark.asyncio
    async def test_upcoming_events(self):
        db = AsyncMock()

        soon = date.today() + timedelta(days=2)
        mock_row = MagicMock()
        mock_row.id = 2
        mock_row.title = "即將到期事件"
        mock_row.end_date = soon
        mock_row.document_id = 20

        overdue_result = MagicMock()
        overdue_result.all.return_value = []

        upcoming_result = MagicMock()
        upcoming_result.all.return_value = [mock_row]

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ProactiveTriggerService(db)
        alerts = await svc.check_document_deadlines()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "deadline_warning"
        assert alerts[0].severity == "warning"  # <= 3 days
        assert alerts[0].metadata["days_remaining"] == 2

    @pytest.mark.asyncio
    async def test_no_deadlines(self):
        db = AsyncMock()

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ProactiveTriggerService(db)
        alerts = await svc.check_document_deadlines()
        assert len(alerts) == 0


class TestCheckProjectDeadlines:
    """案件截止日檢查測試"""

    @pytest.mark.asyncio
    async def test_overdue_project(self):
        db = AsyncMock()

        overdue_date = date.today() - timedelta(days=10)
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.project_name = "道路拓寬案"
        mock_row.end_date = overdue_date
        mock_row.progress = 75

        overdue_result = MagicMock()
        overdue_result.all.return_value = [mock_row]
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ProactiveTriggerService(db)
        alerts = await svc.check_project_deadlines()

        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert alerts[0].entity_type == "project"
        assert "10" in alerts[0].title

    @pytest.mark.asyncio
    async def test_upcoming_project_warning(self):
        db = AsyncMock()

        soon = date.today() + timedelta(days=5)
        mock_row = MagicMock()
        mock_row.id = 2
        mock_row.project_name = "測量案"
        mock_row.end_date = soon
        mock_row.progress = 90

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = [mock_row]

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ProactiveTriggerService(db)
        alerts = await svc.check_project_deadlines()

        assert len(alerts) == 1
        assert alerts[0].severity == "warning"


class TestCheckDataQuality:
    """資料品質檢查測試"""

    @pytest.mark.asyncio
    async def test_no_issues(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        db.execute.return_value = mock_result

        svc = ProactiveTriggerService(db)
        alerts = await svc.check_data_quality()
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_missing_subjects(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 15
        db.execute.return_value = mock_result

        svc = ProactiveTriggerService(db)
        alerts = await svc.check_data_quality()
        assert len(alerts) == 1
        assert alerts[0].alert_type == "data_quality"
        assert alerts[0].severity == "warning"  # > 10


class TestCheckPMMilestoneDeadlines:
    """PM 里程碑逾期檢查測試"""

    @pytest.mark.asyncio
    async def test_overdue_milestone(self):
        db = AsyncMock()

        past_date = date.today() - timedelta(days=20)
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.milestone_name = "設計審查"
        mock_row.planned_date = past_date
        mock_row.pm_case_id = 10
        mock_row.case_code = "CK2025_PM_01_001"
        mock_row.case_name = "測量案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = [mock_row]
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_pm_milestone_deadlines()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "deadline_overdue"
        assert alerts[0].severity == "critical"  # > 14 days
        assert alerts[0].entity_type == "pm_milestone"
        assert "設計審查" in alerts[0].message
        assert "CK2025_PM_01_001" in alerts[0].message

    @pytest.mark.asyncio
    async def test_upcoming_milestone(self):
        db = AsyncMock()

        soon = date.today() + timedelta(days=2)
        mock_row = MagicMock()
        mock_row.id = 2
        mock_row.milestone_name = "成果提交"
        mock_row.planned_date = soon
        mock_row.pm_case_id = 10
        mock_row.case_code = "CK2025_PM_01_001"
        mock_row.case_name = "測量案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = [mock_row]

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_pm_milestone_deadlines()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "deadline_warning"
        assert alerts[0].severity == "warning"  # <= 3 days
        assert alerts[0].metadata["days_remaining"] == 2

    @pytest.mark.asyncio
    async def test_no_pm_milestones(self):
        db = AsyncMock()

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_pm_milestone_deadlines()
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_overdue_warning_severity_boundary(self):
        """逾期 <= 14 天 severity 為 warning"""
        db = AsyncMock()

        past_date = date.today() - timedelta(days=10)
        mock_row = MagicMock()
        mock_row.id = 3
        mock_row.milestone_name = "開工"
        mock_row.planned_date = past_date
        mock_row.pm_case_id = 5
        mock_row.case_code = "CK2025_PM_02_001"
        mock_row.case_name = "規劃案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = [mock_row]
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_pm_milestone_deadlines()

        assert alerts[0].severity == "warning"  # <= 14 days = warning


class TestCheckERPOverdueBillings:
    """ERP 未收款逾期檢查測試"""

    @pytest.mark.asyncio
    async def test_overdue_billing(self):
        db = AsyncMock()

        past_date = date.today() - timedelta(days=75)
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.billing_period = "第2期"
        mock_row.billing_amount = 500000
        mock_row.billing_date = past_date
        mock_row.payment_status = "pending"
        mock_row.case_code = "CK2025_FN_01_001"
        mock_row.case_name = "道路案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = [mock_row]
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_erp_overdue_billings()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "payment_overdue"
        assert alerts[0].severity == "critical"  # > 60 days
        assert alerts[0].entity_type == "erp_billing"
        assert "500,000" in alerts[0].title

    @pytest.mark.asyncio
    async def test_recent_pending_billing(self):
        """請款後 20 天未收款 → warning"""
        db = AsyncMock()

        recent = date.today() - timedelta(days=20)
        mock_row = MagicMock()
        mock_row.id = 2
        mock_row.billing_period = "第1期"
        mock_row.billing_amount = 200000
        mock_row.billing_date = recent
        mock_row.case_code = "CK2025_FN_01_002"
        mock_row.case_name = "規劃案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = [mock_row]

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_erp_overdue_billings()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "payment_warning"
        assert alerts[0].severity == "warning"  # >= 14 days
        assert alerts[0].metadata["days_since_billing"] == 20

    @pytest.mark.asyncio
    async def test_no_overdue_billings(self):
        db = AsyncMock()

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_erp_overdue_billings()
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_partial_payment_is_overdue(self):
        """partial 狀態也算逾期"""
        db = AsyncMock()

        past_date = date.today() - timedelta(days=45)
        mock_row = MagicMock()
        mock_row.id = 3
        mock_row.billing_period = "第3期"
        mock_row.billing_amount = 100000
        mock_row.billing_date = past_date
        mock_row.payment_status = "partial"
        mock_row.case_code = "CK2025_FN_01_003"
        mock_row.case_name = "監造案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = [mock_row]
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_erp_overdue_billings()

        assert len(alerts) == 1
        assert alerts[0].severity == "warning"  # <= 60 days


class TestCheckInvoiceReminder:
    """發票催開預警測試"""

    @pytest.mark.asyncio
    async def test_completed_case_no_invoice(self):
        """已完工案件無發票 → 產生 invoice_reminder 警報"""
        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.case_code = "CK114_PM_01_001"
        mock_row.case_name = "道路拓寬案"
        mock_row.actual_end_date = date.today() - timedelta(days=40)
        mock_row.end_date = date.today() - timedelta(days=45)

        result = MagicMock()
        result.all.return_value = [mock_row]
        db.execute.return_value = result

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_invoice_reminder()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "invoice_reminder"
        assert alerts[0].severity == "critical"  # > 30 days
        assert alerts[0].entity_type == "pm_case"
        assert "道路拓寬案" in alerts[0].message
        assert alerts[0].metadata["days_since_completion"] == 40

    @pytest.mark.asyncio
    async def test_recent_completion_warning(self):
        """完工未滿 30 天 → warning"""
        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.id = 2
        mock_row.case_code = "CK114_PM_01_002"
        mock_row.case_name = "測量案"
        mock_row.actual_end_date = date.today() - timedelta(days=10)
        mock_row.end_date = date.today() - timedelta(days=15)

        result = MagicMock()
        result.all.return_value = [mock_row]
        db.execute.return_value = result

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_invoice_reminder()

        assert len(alerts) == 1
        assert alerts[0].severity == "warning"  # <= 30 days

    @pytest.mark.asyncio
    async def test_no_completed_cases(self):
        """無完工案件 → 無警報"""
        db = AsyncMock()

        result = MagicMock()
        result.all.return_value = []
        db.execute.return_value = result

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_invoice_reminder()
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_fallback_to_end_date(self):
        """無 actual_end_date → 使用 end_date"""
        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.id = 3
        mock_row.case_code = "CK114_PM_01_003"
        mock_row.case_name = "規劃案"
        mock_row.actual_end_date = None
        mock_row.end_date = date.today() - timedelta(days=5)

        result = MagicMock()
        result.all.return_value = [mock_row]
        db.execute.return_value = result

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_invoice_reminder()

        assert len(alerts) == 1
        assert alerts[0].metadata["days_since_completion"] == 5


class TestCheckVendorPaymentMilestones:
    """外包付款里程碑提醒測試"""

    @pytest.mark.asyncio
    async def test_overdue_vendor_payment(self):
        """已逾期的廠商應付 → vendor_payment_overdue"""
        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.vendor_name = "大明工程"
        mock_row.payable_amount = 300000
        mock_row.due_date = date.today() - timedelta(days=20)
        mock_row.description = "第一期外包"
        mock_row.case_code = "CK114_FN_01_001"
        mock_row.case_name = "道路案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = [mock_row]
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_vendor_payment_milestones()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "vendor_payment_overdue"
        assert alerts[0].severity == "critical"  # > 14 days
        assert "大明工程" in alerts[0].message
        assert "300,000" in alerts[0].title
        assert alerts[0].metadata["days_overdue"] == 20

    @pytest.mark.asyncio
    async def test_overdue_warning_boundary(self):
        """逾期 <= 14 天 → warning"""
        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.id = 2
        mock_row.vendor_name = "小華測量"
        mock_row.payable_amount = 50000
        mock_row.due_date = date.today() - timedelta(days=7)
        mock_row.description = "測量費"
        mock_row.case_code = "CK114_FN_01_002"
        mock_row.case_name = "測量案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = [mock_row]
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_vendor_payment_milestones()

        assert alerts[0].severity == "warning"  # <= 14 days

    @pytest.mark.asyncio
    async def test_upcoming_d1_warning(self):
        """D-1 → warning"""
        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.id = 3
        mock_row.vendor_name = "建成機電"
        mock_row.payable_amount = 100000
        mock_row.due_date = date.today() + timedelta(days=1)
        mock_row.description = "機電工程"
        mock_row.case_code = "CK114_FN_01_003"
        mock_row.case_name = "機電案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = [mock_row]

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_vendor_payment_milestones()

        assert len(alerts) == 1
        assert alerts[0].alert_type == "vendor_payment_warning"
        assert alerts[0].severity == "warning"  # D-1

    @pytest.mark.asyncio
    async def test_upcoming_d3_info(self):
        """D-3 → info"""
        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.id = 4
        mock_row.vendor_name = "永興營造"
        mock_row.payable_amount = 200000
        mock_row.due_date = date.today() + timedelta(days=3)
        mock_row.description = "營造費"
        mock_row.case_code = "CK114_FN_01_004"
        mock_row.case_name = "營造案"

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = [mock_row]

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_vendor_payment_milestones()

        assert len(alerts) == 1
        assert alerts[0].severity == "info"  # D-3

    @pytest.mark.asyncio
    async def test_no_pending_payments(self):
        """無待付款項 → 無警報"""
        db = AsyncMock()

        overdue_result = MagicMock()
        overdue_result.all.return_value = []
        upcoming_result = MagicMock()
        upcoming_result.all.return_value = []

        db.execute.side_effect = [overdue_result, upcoming_result]

        svc = ERPTriggerScanner(db)
        alerts = await svc.check_vendor_payment_milestones()
        assert len(alerts) == 0


class TestGetAlertSummary:
    """警報摘要測試"""

    @pytest.mark.asyncio
    async def test_summary_format(self):
        db = AsyncMock()
        svc = ProactiveTriggerService(db)

        # Mock scan_all
        svc.scan_all = AsyncMock(return_value=[
            TriggerAlert("deadline_overdue", "critical", "t1", "m1", "document", 1),
            TriggerAlert("deadline_warning", "warning", "t2", "m2", "project", 2),
            TriggerAlert("data_quality", "info", "t3", "m3", "system"),
        ])

        summary = await svc.get_alert_summary()
        assert summary["total_alerts"] == 3
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["warning"] == 1
        assert summary["by_severity"]["info"] == 1
        assert len(summary["alerts"]) == 3
