# -*- coding: utf-8 -*-
"""
PM/ERP Agent Tools Extended Tests — P4-1

Tests for the new agent tools:
- get_overdue_milestones (PM)
- get_unpaid_billings (ERP)
- ToolRegistry tool count and registration

Run: pytest tests/unit/test_services/test_pm_erp_agent_tools_extended.py -v
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.ai.tools.tool_executor_domain import DomainToolExecutor


@pytest.fixture
def mock_executor(mock_db_session):
    """Create DomainToolExecutor with mocked deps"""
    return DomainToolExecutor(
        db=mock_db_session,
        ai_connector=MagicMock(),
        embedding_mgr=MagicMock(),
        config=MagicMock(),
    )


class TestGetOverdueMilestones:
    """get_overdue_milestones() — P4-1 PM"""

    @pytest.mark.asyncio
    async def test_overdue_milestones_delegates_to_service(self, mock_executor):
        """Verify delegation to PMQueryService.get_overdue_milestones"""
        expected = {"milestones": [{"name": "M1", "overdue_days": 5}], "count": 1}

        with patch("app.services.ai.domain.pm_query_service.PMQueryService") as MockSvc:
            MockSvc.return_value.get_overdue_milestones = AsyncMock(return_value=expected)

            result = await mock_executor.get_overdue_milestones({"limit": 10})

            assert result["count"] == 1
            MockSvc.return_value.get_overdue_milestones.assert_awaited_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_overdue_milestones_limit_capped(self, mock_executor):
        """Limit is capped at 50"""
        with patch("app.services.ai.domain.pm_query_service.PMQueryService") as MockSvc:
            MockSvc.return_value.get_overdue_milestones = AsyncMock(return_value={"milestones": [], "count": 0})

            await mock_executor.get_overdue_milestones({"limit": 100})

            MockSvc.return_value.get_overdue_milestones.assert_awaited_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_overdue_milestones_default_limit(self, mock_executor):
        """Default limit is 20"""
        with patch("app.services.ai.domain.pm_query_service.PMQueryService") as MockSvc:
            MockSvc.return_value.get_overdue_milestones = AsyncMock(return_value={"milestones": [], "count": 0})

            await mock_executor.get_overdue_milestones({})

            MockSvc.return_value.get_overdue_milestones.assert_awaited_once_with(limit=20)

    @pytest.mark.asyncio
    async def test_overdue_milestones_empty_result(self, mock_executor):
        """Empty result returns count 0"""
        with patch("app.services.ai.domain.pm_query_service.PMQueryService") as MockSvc:
            MockSvc.return_value.get_overdue_milestones = AsyncMock(return_value={"milestones": [], "count": 0})

            result = await mock_executor.get_overdue_milestones({"limit": 5})

            assert result["count"] == 0
            assert result["milestones"] == []


class TestGetUnpaidBillings:
    """get_unpaid_billings() — P4-1 ERP"""

    @pytest.mark.asyncio
    async def test_unpaid_billings_delegates_to_service(self, mock_executor):
        """Verify delegation to ERPQueryService.get_unpaid_billings"""
        expected = {"billings": [{"billing_id": 1, "outstanding": "50000"}], "count": 1}

        with patch("app.services.ai.domain.erp_query_service.ERPQueryService") as MockSvc:
            MockSvc.return_value.get_unpaid_billings = AsyncMock(return_value=expected)

            result = await mock_executor.get_unpaid_billings({"limit": 15})

            assert result["count"] == 1
            MockSvc.return_value.get_unpaid_billings.assert_awaited_once_with(limit=15)

    @pytest.mark.asyncio
    async def test_unpaid_billings_limit_capped(self, mock_executor):
        """Limit is capped at 50"""
        with patch("app.services.ai.domain.erp_query_service.ERPQueryService") as MockSvc:
            MockSvc.return_value.get_unpaid_billings = AsyncMock(return_value={"billings": [], "count": 0})

            await mock_executor.get_unpaid_billings({"limit": 200})

            MockSvc.return_value.get_unpaid_billings.assert_awaited_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_unpaid_billings_default_limit(self, mock_executor):
        """Default limit is 20"""
        with patch("app.services.ai.domain.erp_query_service.ERPQueryService") as MockSvc:
            MockSvc.return_value.get_unpaid_billings = AsyncMock(return_value={"billings": [], "count": 0})

            await mock_executor.get_unpaid_billings({})

            MockSvc.return_value.get_unpaid_billings.assert_awaited_once_with(limit=20)

    @pytest.mark.asyncio
    async def test_unpaid_billings_empty_result(self, mock_executor):
        """Empty result returns count 0"""
        with patch("app.services.ai.domain.erp_query_service.ERPQueryService") as MockSvc:
            MockSvc.return_value.get_unpaid_billings = AsyncMock(return_value={"billings": [], "count": 0})

            result = await mock_executor.get_unpaid_billings({"limit": 10})

            assert result["count"] == 0
            assert result["billings"] == []


class TestToolRegistryExtended:
    """ToolRegistry extended tools — P4-1"""

    def test_registry_has_at_least_22_tools(self):
        """ToolRegistry should have >= 22 tools after P4-1"""
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        count = registry.get_tool_count()
        assert count >= 22, f"Expected >= 22 tools, got {count}"

    def test_overdue_milestones_in_registry(self):
        """get_overdue_milestones is registered with PM context"""
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("get_overdue_milestones")
        assert tool is not None, "get_overdue_milestones not found in registry"
        assert tool.contexts is not None
        assert "pm" in tool.contexts

    def test_unpaid_billings_in_registry(self):
        """get_unpaid_billings is registered with ERP context"""
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("get_unpaid_billings")
        assert tool is not None, "get_unpaid_billings not found in registry"
        assert tool.contexts is not None
        assert "erp" in tool.contexts

    def test_overdue_milestones_has_parameters(self):
        """get_overdue_milestones has limit parameter"""
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("get_overdue_milestones")
        assert tool is not None
        assert "limit" in tool.parameters

    def test_unpaid_billings_has_parameters(self):
        """get_unpaid_billings has limit parameter"""
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("get_unpaid_billings")
        assert tool is not None
        assert "limit" in tool.parameters

    def test_overdue_milestones_has_few_shot(self):
        """get_overdue_milestones has few-shot example"""
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("get_overdue_milestones")
        assert tool is not None
        assert tool.few_shot is not None
        assert "question" in tool.few_shot

    def test_unpaid_billings_has_few_shot(self):
        """get_unpaid_billings has few-shot example"""
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()
        tool = registry.get("get_unpaid_billings")
        assert tool is not None
        assert tool.few_shot is not None
        assert "question" in tool.few_shot

    def test_tools_visible_in_context_filter(self):
        """Tools appear when filtering by their context"""
        from app.services.ai.tools.tool_registry import get_tool_registry
        registry = get_tool_registry()

        pm_names = registry.get_valid_names_for_context("pm")
        assert "get_overdue_milestones" in pm_names

        erp_names = registry.get_valid_names_for_context("erp")
        assert "get_unpaid_billings" in erp_names
