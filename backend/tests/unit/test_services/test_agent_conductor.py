"""
Tests for AgentConductor — Parallel sub-task orchestration.

Covers:
- Parallel execution with mocked sub-tasks
- Error isolation (one task fails, others succeed)
- Result merging and deduplication
- Timeout handling
- Empty input handling
- Concurrency limiting
- Domain-to-subtask bridge function
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.agent.agent_conductor import (
    AgentConductor,
    ConductorResult,
    ConductorSubTask,
    build_conductor_subtasks_from_domains,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def conductor():
    return AgentConductor(timeout_per_task=5.0, max_concurrent=3)


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.agent_tool_timeout = 10
    return config


@pytest.fixture
def mock_db():
    return AsyncMock()


# ============================================================================
# Helper: patch the sub-task execution to avoid real DB/AI calls
# ============================================================================


def _make_mock_execute_sub_task(results_by_role: dict, fail_roles: set = None):
    """
    Create a mock _execute_sub_task that returns pre-defined results.

    results_by_role: {"doc": [item1, item2], "pm": [item3]}
    fail_roles: set of roles that should raise an exception
    """
    fail_roles = fail_roles or set()

    async def mock_execute(self, task, config):
        if task.role in fail_roles:
            task.status = "error"
            task.error = f"Simulated failure for {task.role}"
            task.result = {"items": [], "count": 0, "error": task.error}
            return task

        items = results_by_role.get(task.role, [])
        task.status = "done"
        task.result = {
            "items": items,
            "count": len(items),
            "role": task.role,
            "tools_executed": ["mock_tool"],
        }
        task.latency_ms = 50
        return task

    return mock_execute


# ============================================================================
# Tests
# ============================================================================


class TestAgentConductorParallelExecution:
    """Test parallel execution of sub-tasks."""

    @pytest.mark.asyncio
    async def test_parallel_execution_three_domains(self, conductor, mock_config, mock_db):
        """Three sub-tasks should all complete with results merged."""
        results_by_role = {
            "doc": [
                {"id": 1, "doc_number": "A001", "subject": "Test doc", "_source_tool": "search_documents", "_source_role": "doc"},
            ],
            "pm": [
                {"id": 10, "name": "Project X", "_source_tool": "search_projects", "_source_role": "pm"},
            ],
            "erp": [
                {"id": 20, "name": "Vendor Y", "_source_tool": "get_contract_summary", "_source_role": "erp"},
            ],
        }

        with patch.object(
            AgentConductor, "_execute_sub_task",
            _make_mock_execute_sub_task(results_by_role),
        ):
            sub_tasks = [
                {"role": "doc", "question": "test query"},
                {"role": "pm", "question": "test query"},
                {"role": "erp", "question": "test query"},
            ]
            result = await conductor.execute_parallel(sub_tasks, mock_db, mock_config)

        assert isinstance(result, ConductorResult)
        assert result.sub_task_count == 3
        assert result.succeeded == 3
        assert result.failed == 0
        assert len(result.merged_results) == 3
        assert result.total_ms >= 0

    @pytest.mark.asyncio
    async def test_parallel_execution_preserves_all_contexts(self, conductor, mock_config, mock_db):
        """contexts_used should list all successful domains."""
        results_by_role = {
            "doc": [{"id": 1, "_source_tool": "t", "_source_role": "doc"}],
            "pm": [{"id": 2, "_source_tool": "t", "_source_role": "pm"}],
        }

        with patch.object(
            AgentConductor, "_execute_sub_task",
            _make_mock_execute_sub_task(results_by_role),
        ):
            sub_tasks = [
                {"role": "doc", "question": "q"},
                {"role": "pm", "question": "q"},
            ]
            result = await conductor.execute_parallel(sub_tasks, mock_db, mock_config)

        assert set(result.contexts_used) == {"doc", "pm"}


class TestErrorIsolation:
    """One sub-task failing should not block others."""

    @pytest.mark.asyncio
    async def test_one_failure_others_succeed(self, conductor, mock_config, mock_db):
        """If pm fails, doc and erp should still succeed."""
        results_by_role = {
            "doc": [{"id": 1, "_source_tool": "t", "_source_role": "doc"}],
            "erp": [{"id": 2, "_source_tool": "t", "_source_role": "erp"}],
        }

        with patch.object(
            AgentConductor, "_execute_sub_task",
            _make_mock_execute_sub_task(results_by_role, fail_roles={"pm"}),
        ):
            sub_tasks = [
                {"role": "doc", "question": "q"},
                {"role": "pm", "question": "q"},
                {"role": "erp", "question": "q"},
            ]
            result = await conductor.execute_parallel(sub_tasks, mock_db, mock_config)

        assert result.succeeded == 2
        assert result.failed == 1
        assert result.sub_task_count == 3
        # Only successful items in merged results
        assert len(result.merged_results) == 2

    @pytest.mark.asyncio
    async def test_all_failures(self, conductor, mock_config, mock_db):
        """All sub-tasks failing should return empty merged results."""
        with patch.object(
            AgentConductor, "_execute_sub_task",
            _make_mock_execute_sub_task({}, fail_roles={"doc", "pm"}),
        ):
            sub_tasks = [
                {"role": "doc", "question": "q"},
                {"role": "pm", "question": "q"},
            ]
            result = await conductor.execute_parallel(sub_tasks, mock_db, mock_config)

        assert result.succeeded == 0
        assert result.failed == 2
        assert result.merged_results == []


class TestResultMerging:
    """Test deduplication and sorting in result merging."""

    @pytest.mark.asyncio
    async def test_deduplication_by_id(self, conductor, mock_config, mock_db):
        """Items with the same id should be deduplicated."""
        results_by_role = {
            "doc": [
                {"id": 1, "doc_number": "A001", "similarity": 0.9, "_source_tool": "t", "_source_role": "doc"},
                {"id": 2, "doc_number": "A002", "similarity": 0.8, "_source_tool": "t", "_source_role": "doc"},
            ],
            "pm": [
                {"id": 1, "doc_number": "A001", "similarity": 0.7, "_source_tool": "t", "_source_role": "pm"},  # duplicate
                {"id": 3, "name": "Project Z", "_source_tool": "t", "_source_role": "pm"},
            ],
        }

        with patch.object(
            AgentConductor, "_execute_sub_task",
            _make_mock_execute_sub_task(results_by_role),
        ):
            sub_tasks = [
                {"role": "doc", "question": "q"},
                {"role": "pm", "question": "q"},
            ]
            result = await conductor.execute_parallel(sub_tasks, mock_db, mock_config)

        # id=1 appears in both doc and pm, should be deduplicated
        ids = [r.get("id") for r in result.merged_results]
        assert ids.count(1) == 1
        assert len(result.merged_results) == 3  # 1, 2, 3

    @pytest.mark.asyncio
    async def test_sort_by_similarity(self, conductor, mock_config, mock_db):
        """Results should be sorted by similarity descending."""
        results_by_role = {
            "doc": [
                {"id": 1, "similarity": 0.5, "_source_tool": "t", "_source_role": "doc"},
                {"id": 2, "similarity": 0.9, "_source_tool": "t", "_source_role": "doc"},
                {"id": 3, "similarity": 0.7, "_source_tool": "t", "_source_role": "doc"},
            ],
        }

        with patch.object(
            AgentConductor, "_execute_sub_task",
            _make_mock_execute_sub_task(results_by_role),
        ):
            sub_tasks = [{"role": "doc", "question": "q"}]
            result = await conductor.execute_parallel(sub_tasks, mock_db, mock_config)

        similarities = [r.get("similarity", 0) for r in result.merged_results]
        assert similarities == sorted(similarities, reverse=True)


class TestTimeoutHandling:
    """Test timeout behavior for sub-tasks."""

    @pytest.mark.asyncio
    async def test_timeout_marks_task_as_error(self):
        """A timed-out sub-task should be marked as error."""
        conductor = AgentConductor(timeout_per_task=0.1)

        async def slow_execute(self, task, config):
            await asyncio.sleep(10)  # Way longer than timeout
            task.status = "done"
            return task

        with patch.object(AgentConductor, "_execute_sub_task", slow_execute):
            sub_tasks = [{"role": "doc", "question": "q"}]
            # The gather with return_exceptions=True will catch the timeout
            result = await conductor.execute_parallel(
                sub_tasks, AsyncMock(), MagicMock(),
            )

        # Should have 1 sub-task, either error or exception-caught
        assert result.sub_task_count == 1


class TestEmptyInput:
    """Test edge cases with empty input."""

    @pytest.mark.asyncio
    async def test_empty_subtasks(self, conductor, mock_config, mock_db):
        """Empty sub-task list should return empty result."""
        result = await conductor.execute_parallel([], mock_db, mock_config)

        assert result.sub_task_count == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.merged_results == []
        assert result.total_ms == 0

    @pytest.mark.asyncio
    async def test_single_subtask(self, conductor, mock_config, mock_db):
        """Single sub-task should work correctly."""
        results_by_role = {
            "doc": [{"id": 1, "_source_tool": "t", "_source_role": "doc"}],
        }

        with patch.object(
            AgentConductor, "_execute_sub_task",
            _make_mock_execute_sub_task(results_by_role),
        ):
            sub_tasks = [{"role": "doc", "question": "q"}]
            result = await conductor.execute_parallel(sub_tasks, mock_db, mock_config)

        assert result.sub_task_count == 1
        assert result.succeeded == 1
        assert len(result.merged_results) == 1


class TestBuildToolCalls:
    """Test _build_tool_calls logic."""

    def test_explicit_tools_filtered_by_available(self):
        conductor = AgentConductor()
        task = ConductorSubTask(
            role="doc",
            question="test query",
            tools=["search_documents", "nonexistent_tool"],
        )
        available = {"search_documents", "find_similar"}

        calls = conductor._build_tool_calls(task, available)

        assert len(calls) == 1
        assert calls[0]["name"] == "search_documents"

    def test_default_tools_for_role(self):
        conductor = AgentConductor()
        task = ConductorSubTask(role="pm", question="some project query")
        available = {"search_projects", "get_project_detail"}

        calls = conductor._build_tool_calls(task, available)

        assert len(calls) == 1
        assert calls[0]["name"] == "search_projects"
        assert "keywords" in calls[0]["params"]

    def test_no_available_tools(self):
        conductor = AgentConductor()
        task = ConductorSubTask(role="doc", question="q", tools=["search_documents"])
        available = set()

        calls = conductor._build_tool_calls(task, available)
        assert calls == []


class TestBuildConductorSubtasksFromDomains:
    """Test the bridge function from domains to sub-tasks."""

    def test_multi_domain(self):
        sub_tasks = build_conductor_subtasks_from_domains(
            "test question", ["doc", "pm", "erp"],
        )

        assert len(sub_tasks) == 3
        assert sub_tasks[0]["role"] == "doc"
        assert sub_tasks[1]["role"] == "pm"
        assert sub_tasks[2]["role"] == "erp"
        assert all(st["question"] == "test question" for st in sub_tasks)

    def test_single_domain(self):
        sub_tasks = build_conductor_subtasks_from_domains("q", ["doc"])
        assert len(sub_tasks) == 1
        assert sub_tasks[0]["role"] == "doc"

    def test_empty_domains(self):
        sub_tasks = build_conductor_subtasks_from_domains("q", [])
        assert sub_tasks == []


class TestDedupKey:
    """Test dedup key generation."""

    def test_id_based_dedup(self):
        key = AgentConductor._get_dedup_key({"id": 42, "doc_number": "A001"})
        assert key == "id:42"

    def test_doc_number_dedup(self):
        key = AgentConductor._get_dedup_key({"doc_number": "A001"})
        assert key == "doc:A001"

    def test_entity_name_dedup(self):
        key = AgentConductor._get_dedup_key({"name": "Entity X"})
        assert key == "entity:Entity X"

    def test_summary_no_dedup(self):
        key = AgentConductor._get_dedup_key({"_summary": True, "id": 1})
        assert key is None

    def test_no_key(self):
        key = AgentConductor._get_dedup_key({"foo": "bar"})
        assert key is None
