"""
Agent Supervisor 單元測試

Version: 1.0.0
Created: 2026-03-15
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.agent.agent_supervisor import (
    AgentSupervisor,
    SubTask,
    _get_default_calls,
)


class TestDetectDomains:
    """領域偵測測試"""

    def setup_method(self):
        self.supervisor = AgentSupervisor(AsyncMock())

    def test_doc_domain(self):
        domains = self.supervisor.detect_domains("最近的公文有哪些？")
        assert "doc" in domains

    def test_pm_domain(self):
        domains = self.supervisor.detect_domains("執行中的案件進度如何？")
        assert "pm" in domains

    def test_erp_domain(self):
        domains = self.supervisor.detect_domains("協力廠商的合約金額統計")
        assert "erp" in domains

    def test_multi_domain_doc_pm(self):
        domains = self.supervisor.detect_domains("這個案件相關的公文有哪些？")
        assert "doc" in domains
        assert "pm" in domains

    def test_multi_domain_pm_erp(self):
        domains = self.supervisor.detect_domains("案件的廠商配合和合約金額")
        assert "pm" in domains
        assert "erp" in domains

    def test_dispatch_detected(self):
        domains = self.supervisor.detect_domains("派工單的進度如何？")
        assert "dispatch" in domains

    def test_default_to_doc(self):
        domains = self.supervisor.detect_domains("你好")
        assert domains == ["doc"]

    def test_all_three_domains(self):
        domains = self.supervisor.detect_domains("這個案件的公文和廠商合約")
        assert len(domains) >= 2


class TestIsMultiDomain:
    """多領域判斷測試"""

    def setup_method(self):
        self.supervisor = AgentSupervisor(AsyncMock())

    def test_single_domain(self):
        assert not self.supervisor.is_multi_domain("最近的公文")

    def test_multi_domain(self):
        assert self.supervisor.is_multi_domain("案件的公文和廠商")


class TestDecomposeQuestion:
    """問題拆解測試"""

    def setup_method(self):
        self.supervisor = AgentSupervisor(AsyncMock())

    @pytest.mark.asyncio
    async def test_creates_subtask_per_domain(self):
        subtasks = await self.supervisor.decompose_question(
            "案件和公文", ["doc", "pm"]
        )
        assert len(subtasks) == 2
        assert subtasks[0].context == "doc"
        assert subtasks[1].context == "pm"
        assert all(st.status == "pending" for st in subtasks)

    @pytest.mark.asyncio
    async def test_single_domain(self):
        subtasks = await self.supervisor.decompose_question("公文查詢", ["doc"])
        assert len(subtasks) == 1


class TestMergeResults:
    """結果合併測試"""

    def setup_method(self):
        self.supervisor = AgentSupervisor(AsyncMock())

    def test_merge_single(self):
        subtasks = [
            SubTask(
                context="doc",
                question="test",
                results=[{"documents": [{"id": 1}], "count": 1}],
                status="done",
            ),
        ]
        merged = self.supervisor.merge_results(subtasks)
        assert "公文搜尋結果" in merged
        assert '"count": 1' in merged

    def test_merge_multi(self):
        subtasks = [
            SubTask(context="doc", question="test",
                    results=[{"count": 1}], status="done"),
            SubTask(context="pm", question="test",
                    results=[{"count": 2}], status="done"),
        ]
        merged = self.supervisor.merge_results(subtasks)
        assert "公文搜尋結果" in merged
        assert "專案管理結果" in merged

    def test_skip_error_subtasks(self):
        subtasks = [
            SubTask(context="doc", question="test",
                    results=[{"error": "fail"}], status="error"),
        ]
        merged = self.supervisor.merge_results(subtasks)
        assert merged == "(所有子任務均無結果)"

    def test_empty_results(self):
        subtasks = [
            SubTask(context="doc", question="test",
                    results=[{"count": 0}], status="done"),
        ]
        merged = self.supervisor.merge_results(subtasks)
        assert "(無結果)" in merged


class TestGetDefaultCalls:
    """預設工具呼叫測試"""

    def test_doc_context(self):
        calls = _get_default_calls("doc", "工務局的函")
        assert len(calls) == 1
        assert calls[0]["name"] == "search_documents"

    def test_pm_context(self):
        calls = _get_default_calls("pm", "案件進度")
        assert len(calls) == 1
        assert calls[0]["name"] == "search_projects"

    def test_erp_context(self):
        calls = _get_default_calls("erp", "合約金額")
        assert len(calls) == 1
        assert calls[0]["name"] == "get_contract_summary"

    def test_unknown_context(self):
        calls = _get_default_calls("unknown", "test")
        assert calls == []


class TestOrchestrate:
    """完整編排流程測試"""

    @pytest.mark.asyncio
    async def test_orchestrate_returns_result(self):
        db = AsyncMock()
        supervisor = AgentSupervisor(db)

        # Mock execute_subtasks to avoid real tool execution
        async def mock_execute(subtasks, tool_timeout):
            for st in subtasks:
                st.status = "done"
                st.results = [{"count": 1}]
            return subtasks

        supervisor.execute_subtasks = mock_execute

        result = await supervisor.orchestrate("案件的公文和廠商合約")
        assert result.contexts_used
        assert result.merged_context
        assert isinstance(result.subtasks, list)
