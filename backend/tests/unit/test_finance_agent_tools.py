"""
Finance Agent Tools 整合測試

測試範圍:
- tool_definitions: 財務工具定義正確性 (3 tools)
- tool_executor_domain: 財務工具執行邏輯
- proactive_triggers_erp: 預算超支掃描 + 待核銷提醒
- agent_tools dispatch: 工具路由一致性
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================
# Tool Registry Tests
# ============================================================

class TestFinanceToolRegistry:
    """財務工具註冊驗證"""

    def test_finance_tools_registered(self):
        """確認 3 個財務工具已註冊"""
        from app.services.ai.tool_registry import get_tool_registry

        registry = get_tool_registry()
        names = registry.valid_tool_names

        assert "get_financial_summary" in names
        assert "get_expense_overview" in names
        assert "check_budget_alert" in names

    def test_finance_tools_in_erp_context(self):
        """財務工具應出現在 erp context"""
        from app.services.ai.tool_registry import get_tool_registry

        registry = get_tool_registry()
        erp_tools = registry.get_valid_names_for_context("erp")

        assert "get_financial_summary" in erp_tools
        assert "get_expense_overview" in erp_tools
        assert "check_budget_alert" in erp_tools

    def test_financial_summary_in_pm_context(self):
        """get_financial_summary 與 check_budget_alert 也應在 pm context"""
        from app.services.ai.tool_registry import get_tool_registry

        registry = get_tool_registry()
        pm_tools = registry.get_valid_names_for_context("pm")

        assert "get_financial_summary" in pm_tools
        assert "check_budget_alert" in pm_tools

    def test_finance_tool_definitions_have_few_shot(self):
        """財務工具應有 few_shot 範例"""
        from app.services.ai.tool_registry import get_tool_registry

        registry = get_tool_registry()
        for name in ["get_financial_summary", "get_expense_overview", "check_budget_alert"]:
            tool = registry._tools[name]
            assert tool.few_shot is not None, f"{name} missing few_shot"
            assert "question" in tool.few_shot
            assert "response_json" in tool.few_shot

    def test_finance_query_type_keywords(self):
        """finance 查詢類型關鍵字應觸發正確工具"""
        from app.services.ai.tool_registry import get_tool_registry

        registry = get_tool_registry()
        detected = registry._detect_query_types("公司今年的財務狀況如何？")
        assert "finance" in detected

    def test_finance_tool_suggestion(self):
        """財務相關查詢應推薦 get_financial_summary"""
        from app.services.ai.tool_registry import get_tool_registry

        registry = get_tool_registry()
        # Sync suggest (without DB)
        detected = registry._detect_query_types("預算超支的案件有哪些")
        assert "finance" in detected


# ============================================================
# Dispatch Consistency Tests
# ============================================================

class TestFinanceDispatchConsistency:
    """財務工具路由一致性"""

    def test_dispatch_keys_include_finance_tools(self):
        """_DISPATCH_KEYS 包含財務工具"""
        from app.services.ai.agent_tools import _DISPATCH_KEYS

        assert "get_financial_summary" in _DISPATCH_KEYS
        assert "get_expense_overview" in _DISPATCH_KEYS
        assert "check_budget_alert" in _DISPATCH_KEYS

    def test_dispatch_map_consistency(self):
        """dispatch keys 與 registry 非 skill 工具完全一致"""
        # 如果不一致，agent_tools 模組載入時會拋出 RuntimeError
        # 能成功 import 就代表通過
        from app.services.ai.agent_tools import VALID_TOOL_NAMES
        assert len(VALID_TOOL_NAMES) >= 27  # 24 原有 + 3 新增

    def test_guard_templates_include_finance(self):
        """ToolResultGuard 包含財務工具回退模板"""
        from app.services.ai.agent_tools import ToolResultGuard

        templates = ToolResultGuard._GUARD_TEMPLATES
        assert "get_financial_summary" in templates
        assert "get_expense_overview" in templates
        assert "check_budget_alert" in templates


# ============================================================
# Tool Executor Tests
# ============================================================

class TestFinanceToolExecutor:
    """財務工具執行器測試"""

    def _make_executor(self, db_mock=None):
        from app.services.ai.tool_executor_domain import DomainToolExecutor

        db = db_mock or AsyncMock()
        return DomainToolExecutor(
            db=db,
            ai_connector=MagicMock(),
            embedding_mgr=MagicMock(),
            config=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_get_financial_summary_company(self):
        """測試公司財務總覽查詢"""
        executor = self._make_executor()

        mock_overview = {
            "total_revenue": 5000000,
            "total_expenses": 3200000,
            "total_balance": 1800000,
            "top_projects": [],
        }

        with patch(
            "app.services.financial_summary_service.FinancialSummaryService.get_company_overview",
            new_callable=AsyncMock,
            return_value=mock_overview,
        ):
            result = await executor.get_financial_summary({"year": 115, "top_n": 5})

        assert result["type"] == "company"
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_get_financial_summary_project(self):
        """測試單一專案財務查詢"""
        executor = self._make_executor()

        mock_summary = {
            "case_code": "A-115-001",
            "revenue": 1000000,
            "expenses": 500000,
        }

        with patch(
            "app.services.financial_summary_service.FinancialSummaryService.get_project_summary",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            result = await executor.get_financial_summary({"case_code": "A-115-001"})

        assert result["type"] == "project"
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_get_expense_overview(self):
        """測試費用報銷查詢"""
        executor = self._make_executor()

        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.inv_num = "AB12345678"
        mock_invoice.date = date(2026, 3, 21)
        mock_invoice.amount = Decimal("2500")
        mock_invoice.category = "文具及印刷"
        mock_invoice.status = "pending"
        mock_invoice.case_code = "A-115-001"
        mock_invoice.description = "原子筆"

        with patch(
            "app.services.expense_invoice_service.ExpenseInvoiceService.query",
            new_callable=AsyncMock,
            return_value=([mock_invoice], 1),
        ):
            result = await executor.get_expense_overview({"status": "pending", "limit": 10})

        assert result["count"] == 1
        assert result["total"] == 1
        assert result["items"][0]["inv_num"] == "AB12345678"
        assert result["items"][0]["amount"] == 2500.0

    @pytest.mark.asyncio
    async def test_check_budget_alert_with_warnings(self):
        """測試預算超支警報 — 有超支案件"""
        executor = self._make_executor()

        mock_overview = {
            "top_projects": [
                {"case_code": "A-115-001", "revenue": 1000000, "expenses": 950000},
                {"case_code": "A-115-002", "revenue": 500000, "expenses": 200000},
                {"case_code": "A-115-003", "revenue": 800000, "expenses": 850000},
            ],
        }

        with patch(
            "app.services.financial_summary_service.FinancialSummaryService.get_company_overview",
            new_callable=AsyncMock,
            return_value=mock_overview,
        ):
            result = await executor.check_budget_alert({"threshold_pct": 80})

        # A-115-001: 95% → warning, A-115-003: 106.25% → critical
        assert result["count"] == 2
        alerts = result["alerts"]
        codes = [a["case_code"] for a in alerts]
        assert "A-115-001" in codes
        assert "A-115-003" in codes
        # A-115-002: 40% → no alert
        assert "A-115-002" not in codes

        # Check levels
        for a in alerts:
            if a["case_code"] == "A-115-003":
                assert a["level"] == "critical"
            elif a["case_code"] == "A-115-001":
                assert a["level"] == "warning"

    @pytest.mark.asyncio
    async def test_check_budget_alert_no_alerts(self):
        """測試預算超支警報 — 無超支"""
        executor = self._make_executor()

        mock_overview = {
            "top_projects": [
                {"case_code": "A-115-001", "revenue": 1000000, "expenses": 100000},
            ],
        }

        with patch(
            "app.services.financial_summary_service.FinancialSummaryService.get_company_overview",
            new_callable=AsyncMock,
            return_value=mock_overview,
        ):
            result = await executor.check_budget_alert({"threshold_pct": 80})

        assert result["count"] == 0
        assert result["alerts"] == []


# ============================================================
# Proactive Triggers Tests
# ============================================================

class TestFinanceProactiveTriggers:
    """財務主動觸發測試"""

    @pytest.mark.asyncio
    async def test_budget_overrun_trigger(self):
        """預算超支掃描應產生警報"""
        from app.services.ai.proactive_triggers_finance import check_budget_overrun

        db = AsyncMock()

        # 模擬聚合結果
        mock_row = MagicMock()
        mock_row.case_code = "A-115-001"
        mock_row.total_income = Decimal("1000000")
        mock_row.total_expense = Decimal("950000")

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db.execute = AsyncMock(return_value=mock_result)

        alerts = await check_budget_overrun(db, threshold_pct=80)

        assert len(alerts) == 1
        assert alerts[0].alert_type == "budget_overrun"
        assert alerts[0].severity == "warning"
        assert alerts[0].metadata["usage_pct"] == 95.0

    @pytest.mark.asyncio
    async def test_budget_overrun_critical(self):
        """支出超過收入應為 critical"""
        from app.services.ai.proactive_triggers_finance import check_budget_overrun

        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.case_code = "A-115-002"
        mock_row.total_income = Decimal("500000")
        mock_row.total_expense = Decimal("600000")

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db.execute = AsyncMock(return_value=mock_result)

        alerts = await check_budget_overrun(db, threshold_pct=80)

        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert alerts[0].metadata["usage_pct"] == 120.0

    @pytest.mark.asyncio
    async def test_budget_overrun_skip_zero_income(self):
        """收入為 0 的專案不應觸發警報"""
        from app.services.ai.proactive_triggers_finance import check_budget_overrun

        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.case_code = "A-115-003"
        mock_row.total_income = Decimal("0")
        mock_row.total_expense = Decimal("100000")

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db.execute = AsyncMock(return_value=mock_result)

        alerts = await check_budget_overrun(db, threshold_pct=80)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_pending_receipts_trigger(self):
        """待核銷發票掃描應產生提醒"""
        from app.services.ai.proactive_triggers_finance import check_pending_receipts

        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 8
        db.execute = AsyncMock(return_value=mock_result)

        alerts = await check_pending_receipts(db, stale_days=7)

        assert len(alerts) == 1
        assert alerts[0].alert_type == "pending_receipt_stale"
        assert alerts[0].severity == "warning"  # >= 5
        assert alerts[0].metadata["stale_count"] == 8

    @pytest.mark.asyncio
    async def test_pending_receipts_none(self):
        """無待核銷發票不應產生提醒"""
        from app.services.ai.proactive_triggers_finance import check_pending_receipts

        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)

        alerts = await check_pending_receipts(db, stale_days=7)

        assert len(alerts) == 0
