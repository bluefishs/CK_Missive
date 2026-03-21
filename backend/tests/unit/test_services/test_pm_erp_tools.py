"""
PM/ERP Agent 工具測試

測試 PMQueryService, ERPQueryService, 以及 ToolRegistry 擴展

Version: 1.0.0
Created: 2026-03-15
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── ToolRegistry 18 工具測試 ──


class TestToolRegistryExpansion:
    """驗證 ToolRegistry 包含 18 個工具"""

    def test_registry_has_at_least_26_manual_tools(self):
        from app.services.ai.tool_registry import ToolRegistry, _register_default_tools

        registry = ToolRegistry()
        _register_default_tools(registry)
        # 26 manual tools (23 original + 3 finance) + auto-discovered skill tools
        non_skill = {n for n in registry.valid_tool_names if not n.startswith("skill_")}
        assert len(non_skill) == 26
        assert registry.get_tool_count() >= 26

    def test_pm_tools_registered(self):
        from app.services.ai.tool_registry import ToolRegistry, _register_default_tools

        registry = ToolRegistry()
        _register_default_tools(registry)
        pm_tools = {"search_projects", "get_project_detail", "get_project_progress"}
        assert pm_tools.issubset(registry.valid_tool_names)

    def test_erp_tools_registered(self):
        from app.services.ai.tool_registry import ToolRegistry, _register_default_tools

        registry = ToolRegistry()
        _register_default_tools(registry)
        erp_tools = {"search_vendors", "get_vendor_detail", "get_contract_summary"}
        assert erp_tools.issubset(registry.valid_tool_names)

    def test_pm_context_filter(self):
        from app.services.ai.tool_registry import ToolRegistry, _register_default_tools

        registry = ToolRegistry()
        _register_default_tools(registry)
        pm_names = registry.get_valid_names_for_context("pm")
        assert "search_projects" in pm_names
        assert "get_project_detail" in pm_names
        assert "get_project_progress" in pm_names
        # get_contract_summary is in both pm and erp
        assert "get_contract_summary" in pm_names

    def test_erp_context_filter(self):
        from app.services.ai.tool_registry import ToolRegistry, _register_default_tools

        registry = ToolRegistry()
        _register_default_tools(registry)
        erp_names = registry.get_valid_names_for_context("erp")
        assert "search_vendors" in erp_names
        assert "get_vendor_detail" in erp_names
        assert "get_contract_summary" in erp_names
        # PM-only tools should NOT be in erp context
        assert "search_projects" not in erp_names

    def test_no_context_returns_all(self):
        from app.services.ai.tool_registry import ToolRegistry, _register_default_tools

        registry = ToolRegistry()
        _register_default_tools(registry)
        all_names = registry.get_valid_names_for_context(None)
        assert len(all_names) >= 22

    def test_few_shot_exists_for_pm_erp(self):
        from app.services.ai.tool_registry import ToolRegistry, _register_default_tools

        registry = ToolRegistry()
        _register_default_tools(registry)
        # These tools should have few_shot
        for name in ["search_projects", "get_project_progress", "search_vendors", "get_contract_summary"]:
            tool = registry.get(name)
            assert tool is not None, f"{name} not found"
            assert tool.few_shot is not None, f"{name} has no few_shot"


# ── ToolResultGuard 18 模板測試 ──


class TestToolResultGuardExpansion:
    """驗證 ToolResultGuard 包含 PM/ERP 回退模板"""

    def test_guard_templates_cover_all_non_skill_tools(self):
        from app.services.ai.agent_tools import ToolResultGuard, VALID_TOOL_NAMES

        for name in VALID_TOOL_NAMES:
            if name.startswith("skill_"):
                continue  # skill tools handled dynamically in guard()
            assert name in ToolResultGuard._GUARD_TEMPLATES, f"Missing guard for {name}"

    def test_pm_guard_search_projects(self):
        from app.services.ai.agent_tools import ToolResultGuard

        result = ToolResultGuard.guard(
            "search_projects", {}, {"error": "timeout", "count": 0}
        )
        assert result["guarded"] is True
        assert result["projects"] == []

    def test_erp_guard_search_vendors(self):
        from app.services.ai.agent_tools import ToolResultGuard

        result = ToolResultGuard.guard(
            "search_vendors", {}, {"error": "timeout", "count": 0}
        )
        assert result["guarded"] is True
        assert result["vendors"] == []

    def test_erp_guard_contract_summary(self):
        from app.services.ai.agent_tools import ToolResultGuard

        result = ToolResultGuard.guard(
            "get_contract_summary", {}, {"error": "db error", "count": 0}
        )
        assert result["guarded"] is True
        assert result["summary"] == {}


# ── PMQueryService 測試 ──


class TestPMQueryService:
    """PMQueryService 單元測試"""

    def _mock_db(self):
        db = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_search_projects_empty(self):
        db = self._mock_db()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        from app.services.ai.pm_query_service import PMQueryService
        svc = PMQueryService(db)
        result = await svc.search_projects(keywords=["不存在"])
        assert result["count"] == 0
        assert result["projects"] == []

    @pytest.mark.asyncio
    async def test_search_projects_with_results(self):
        db = self._mock_db()
        mock_project = MagicMock()
        mock_project.id = 1
        mock_project.project_name = "測量案件"
        mock_project.project_code = "P001"
        mock_project.year = 115
        mock_project.status = "執行中"
        mock_project.client_agency = "桃園市政府工務局"
        mock_project.category = "測量"
        mock_project.contract_amount = 1000000
        mock_project.progress = 50
        mock_project.start_date = None
        mock_project.end_date = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_project]
        db.execute.return_value = mock_result

        from app.services.ai.pm_query_service import PMQueryService
        svc = PMQueryService(db)
        result = await svc.search_projects(status="執行中")
        assert result["count"] == 1
        assert result["projects"][0]["project_name"] == "測量案件"

    @pytest.mark.asyncio
    async def test_get_project_detail_not_found(self):
        db = self._mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        from app.services.ai.pm_query_service import PMQueryService
        svc = PMQueryService(db)
        result = await svc.get_project_detail(999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_project_progress_not_found(self):
        db = self._mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        from app.services.ai.pm_query_service import PMQueryService
        svc = PMQueryService(db)
        result = await svc.get_project_progress(999)
        assert "error" in result


# ── ERPQueryService 測試 ──


class TestERPQueryService:
    """ERPQueryService 單元測試"""

    def _mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_search_vendors_empty(self):
        db = self._mock_db()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        from app.services.ai.erp_query_service import ERPQueryService
        svc = ERPQueryService(db)
        result = await svc.search_vendors(keywords=["不存在"])
        assert result["count"] == 0
        assert result["vendors"] == []

    @pytest.mark.asyncio
    async def test_search_vendors_with_results(self):
        db = self._mock_db()
        mock_vendor = MagicMock()
        mock_vendor.id = 1
        mock_vendor.vendor_name = "測量公司A"
        mock_vendor.vendor_code = "V001"
        mock_vendor.contact_person = "張三"
        mock_vendor.phone = "02-1234567"
        mock_vendor.business_type = "測量"
        mock_vendor.rating = 5

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_vendor]
        db.execute.return_value = mock_result

        from app.services.ai.erp_query_service import ERPQueryService
        svc = ERPQueryService(db)
        result = await svc.search_vendors(keywords=["測量"])
        assert result["count"] == 1
        assert result["vendors"][0]["vendor_name"] == "測量公司A"

    @pytest.mark.asyncio
    async def test_get_vendor_detail_not_found(self):
        db = self._mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        from app.services.ai.erp_query_service import ERPQueryService
        svc = ERPQueryService(db)
        result = await svc.get_vendor_detail(999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_contract_summary(self):
        db = self._mock_db()

        # Mock stats query
        mock_stats_row = MagicMock()
        mock_stats_row.total_projects = 5
        mock_stats_row.total_contract_amount = 5000000
        mock_stats_row.total_winning_amount = 4500000
        mock_stats_row.avg_progress = 60.5

        mock_stats_result = MagicMock()
        mock_stats_result.one.return_value = mock_stats_row

        # Mock status distribution
        mock_status_row = MagicMock()
        mock_status_row.status = "執行中"
        mock_status_row.count = 3
        mock_status_row.amount = 3000000

        mock_status_result = MagicMock()
        mock_status_result.all.return_value = [mock_status_row]

        # Mock year distribution
        mock_year_row = MagicMock()
        mock_year_row.year = 115
        mock_year_row.count = 5
        mock_year_row.amount = 5000000

        mock_year_result = MagicMock()
        mock_year_result.all.return_value = [mock_year_row]

        db.execute.side_effect = [mock_stats_result, mock_status_result, mock_year_result]

        from app.services.ai.erp_query_service import ERPQueryService
        svc = ERPQueryService(db)
        result = await svc.get_contract_summary()
        assert result["count"] == 1
        assert result["summary"]["total_projects"] == 5
        assert result["summary"]["total_contract_amount"] == 5000000


# ── AgentToolExecutor dispatch_map 一致性測試 ──


class TestDispatchMapConsistency:
    """確認 dispatch_map 與 ToolRegistry 一致"""

    def test_dispatch_keys_match_non_skill_registry(self):
        from app.services.ai.agent_tools import _DISPATCH_KEYS, VALID_TOOL_NAMES
        non_skill = {n for n in VALID_TOOL_NAMES if not n.startswith("skill_")}
        assert _DISPATCH_KEYS == non_skill
