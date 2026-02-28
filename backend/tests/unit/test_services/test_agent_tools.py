"""
Agent 工具模組單元測試

測試範圍：
- TOOL_DEFINITIONS / VALID_TOOL_NAMES 常數正確性
- ENTITY_TYPE_MAP 映射
- AgentToolExecutor.execute 路由
- 各工具的參數處理與回傳格式

共 25+ test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.agent_tools import (
    TOOL_DEFINITIONS,
    TOOL_DEFINITIONS_STR,
    VALID_TOOL_NAMES,
    ENTITY_TYPE_MAP,
    AgentToolExecutor,
)


# ============================================================================
# 常數測試
# ============================================================================

class TestToolConstants:
    """工具常數測試"""

    def test_tool_definitions_count(self):
        assert len(TOOL_DEFINITIONS) == 6

    def test_all_tools_have_required_fields(self):
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool

    def test_valid_tool_names_matches_definitions(self):
        expected = {t["name"] for t in TOOL_DEFINITIONS}
        assert VALID_TOOL_NAMES == expected

    def test_tool_definitions_str_is_json(self):
        import json
        parsed = json.loads(TOOL_DEFINITIONS_STR)
        assert len(parsed) == 6

    def test_expected_tool_names(self):
        expected = {
            "search_documents",
            "search_entities",
            "get_entity_detail",
            "find_similar",
            "search_dispatch_orders",
            "get_statistics",
        }
        assert VALID_TOOL_NAMES == expected


class TestEntityTypeMap:
    """entity_type 映射測試"""

    @pytest.mark.parametrize("input_type,expected", [
        ("organization", "org"),
        ("organisation", "org"),
        ("機關", "org"),
        ("人員", "person"),
        ("人", "person"),
        ("專案", "project"),
        ("案件", "project"),
        ("地點", "location"),
        ("地址", "location"),
        ("主題", "topic"),
        ("議題", "topic"),
        ("日期", "date"),
        ("時間", "date"),
    ])
    def test_type_mapping(self, input_type, expected):
        assert ENTITY_TYPE_MAP[input_type] == expected


# ============================================================================
# AgentToolExecutor
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_ai():
    return AsyncMock()


@pytest.fixture
def mock_embedding_mgr():
    mgr = MagicMock()
    mgr.get_embedding = AsyncMock(return_value=None)
    return mgr


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.hybrid_semantic_weight = 0.3
    return config


@pytest.fixture
def executor(mock_db, mock_ai, mock_embedding_mgr, mock_config):
    return AgentToolExecutor(mock_db, mock_ai, mock_embedding_mgr, mock_config)


class TestToolExecutorRouting:
    """工具路由測試"""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, executor):
        result = await executor.execute("nonexistent_tool", {})
        assert "error" in result
        assert "未知工具" in result["error"]

    @pytest.mark.asyncio
    async def test_dispatch_to_search_entities(self, executor):
        with patch(
            "app.services.ai.agent_tools.AgentToolExecutor._search_entities",
            new_callable=AsyncMock,
            return_value={"entities": [], "count": 0},
        ) as mock:
            result = await executor.execute("search_entities", {"query": "test"})
            mock.assert_called_once_with({"query": "test"})
            assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_dispatch_to_get_statistics(self, executor):
        with patch(
            "app.services.ai.agent_tools.AgentToolExecutor._get_statistics",
            new_callable=AsyncMock,
            return_value={"stats": {}, "top_entities": [], "count": 1},
        ) as mock:
            result = await executor.execute("get_statistics", {})
            mock.assert_called_once()
            assert result["count"] == 1


class TestSearchEntities:
    """search_entities 工具測試"""

    @pytest.mark.asyncio
    async def test_entity_type_normalization(self, executor):
        """LLM 可能傳入 organization → 應正規化為 org"""
        mock_svc = MagicMock()
        mock_svc.search_entities = AsyncMock(return_value=[])

        with patch(
            "app.services.ai.graph_query_service.GraphQueryService",
            return_value=mock_svc,
        ):
            result = await executor._search_entities({
                "query": "test",
                "entity_type": "organization",
                "limit": 5,
            })
            mock_svc.search_entities.assert_called_once_with(
                "test", entity_type="org", limit=5
            )

    @pytest.mark.asyncio
    async def test_limit_cap(self, executor):
        """limit 不應超過 20"""
        mock_svc = MagicMock()
        mock_svc.search_entities = AsyncMock(return_value=[])

        with patch(
            "app.services.ai.graph_query_service.GraphQueryService",
            return_value=mock_svc,
        ):
            await executor._search_entities({"query": "test", "limit": 100})
            _, kwargs = mock_svc.search_entities.call_args
            assert kwargs["limit"] == 20


class TestGetEntityDetail:
    """get_entity_detail 工具測試"""

    @pytest.mark.asyncio
    async def test_missing_entity_id(self, executor):
        result = await executor._get_entity_detail({})
        assert "error" in result
        assert "entity_id" in result["error"]

    @pytest.mark.asyncio
    async def test_entity_not_found(self, executor):
        mock_svc = MagicMock()
        mock_svc.get_entity_detail = AsyncMock(return_value=None)

        with patch(
            "app.services.ai.graph_query_service.GraphQueryService",
            return_value=mock_svc,
        ):
            result = await executor._get_entity_detail({"entity_id": 999})
            assert "error" in result
            assert "999" in result["error"]

    @pytest.mark.asyncio
    async def test_entity_found(self, executor):
        detail = {
            "canonical_name": "工務局",
            "documents": [{"id": 1}],
            "relationships": [{"id": 1}],
        }
        mock_svc = MagicMock()
        mock_svc.get_entity_detail = AsyncMock(return_value=detail)

        with patch(
            "app.services.ai.graph_query_service.GraphQueryService",
            return_value=mock_svc,
        ):
            result = await executor._get_entity_detail({"entity_id": 1})
            assert result["count"] == 1
            assert result["entity"]["canonical_name"] == "工務局"


class TestFindSimilar:
    """find_similar 工具測試"""

    @pytest.mark.asyncio
    async def test_missing_document_id(self, executor):
        result = await executor._find_similar({})
        assert "error" in result
        assert "document_id" in result["error"]

    @pytest.mark.asyncio
    async def test_document_not_found(self, executor):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        executor.db.execute.return_value = mock_result

        result = await executor._find_similar({"document_id": 999})
        assert "error" in result
        assert "999" in result["error"]


class TestGetStatistics:
    """get_statistics 工具測試"""

    @pytest.mark.asyncio
    async def test_returns_stats(self, executor):
        mock_svc = MagicMock()
        mock_svc.get_graph_stats = AsyncMock(return_value={"total_entities": 100})
        mock_svc.get_top_entities = AsyncMock(return_value=[{"name": "A"}])

        with patch(
            "app.services.ai.graph_query_service.GraphQueryService",
            return_value=mock_svc,
        ):
            result = await executor._get_statistics({})
            assert result["count"] == 1
            assert result["stats"]["total_entities"] == 100
            assert len(result["top_entities"]) == 1


class TestExecuteParallel:
    """execute_parallel 並行執行測試（OPT-2）"""

    @pytest.mark.asyncio
    async def test_parallel_two_tools_success(self, executor):
        """兩個工具並行執行成功"""
        calls = [
            {"name": "search_entities", "params": {"query": "test", "limit": 5}},
            {"name": "get_statistics", "params": {}},
        ]

        mock_svc = MagicMock()
        mock_svc.search_entities = AsyncMock(return_value=[{"id": 1}])
        mock_svc.get_graph_stats = AsyncMock(return_value={"total": 10})
        mock_svc.get_top_entities = AsyncMock(return_value=[])

        with patch(
            "app.services.ai.graph_query_service.GraphQueryService",
            return_value=mock_svc,
        ), patch(
            "app.db.database.AsyncSessionLocal",
        ) as mock_session_cls:
            # Mock AsyncSessionLocal 的 async context manager
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            # 因為 execute_parallel 內部建立新 executor，
            # 需要 patch 整個 AgentToolExecutor 類的內部方法
            # 改用更直接的方式：mock execute 方法
            with patch.object(
                AgentToolExecutor, "execute",
                new_callable=AsyncMock,
                side_effect=[
                    {"entities": [{"id": 1}], "count": 1},
                    {"stats": {"total": 10}, "top_entities": [], "count": 1},
                ],
            ):
                results = await executor.execute_parallel(calls, tool_timeout=15)

            assert len(results) == 2
            assert results[0]["count"] == 1
            assert results[1]["count"] == 1

    @pytest.mark.asyncio
    async def test_parallel_one_tool_fails(self, executor):
        """一個工具失敗不影響其他工具"""
        calls = [
            {"name": "search_documents", "params": {"keywords": ["test"]}},
            {"name": "search_entities", "params": {"query": "test"}},
        ]

        with patch(
            "app.db.database.AsyncSessionLocal",
        ) as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            call_count = 0
            async def side_effect_fn(tool_name, params):
                nonlocal call_count
                call_count += 1
                if tool_name == "search_documents":
                    raise ValueError("DB error")
                return {"entities": [], "count": 0}

            with patch.object(
                AgentToolExecutor, "execute",
                new_callable=AsyncMock,
                side_effect=side_effect_fn,
            ):
                results = await executor.execute_parallel(calls, tool_timeout=15)

            assert len(results) == 2
            # 第一個失敗，應有 error
            assert "error" in results[0]
            assert "DB error" in results[0]["error"]
            # 第二個成功
            assert results[1]["count"] == 0

    @pytest.mark.asyncio
    async def test_parallel_timeout(self, executor):
        """工具超時處理"""
        import asyncio

        calls = [
            {"name": "search_documents", "params": {"keywords": ["test"]}},
        ]

        with patch(
            "app.db.database.AsyncSessionLocal",
        ) as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            async def slow_execute(tool_name, params):
                await asyncio.sleep(100)

            with patch.object(
                AgentToolExecutor, "execute",
                new_callable=AsyncMock,
                side_effect=slow_execute,
            ):
                results = await executor.execute_parallel(calls, tool_timeout=0.01)

            assert len(results) == 1
            assert "error" in results[0]
            assert "超時" in results[0]["error"]

    @pytest.mark.asyncio
    async def test_parallel_empty_calls(self, executor):
        """空呼叫列表"""
        results = await executor.execute_parallel([], tool_timeout=15)
        assert results == []


class TestSearchDispatchOrders:
    """search_dispatch_orders 工具測試"""

    @pytest.mark.asyncio
    async def test_dispatch_no_strategy(self, executor):
        """策略 1: 精確派工單號查詢"""
        mock_repo = MagicMock()
        mock_repo.filter_dispatch_orders = AsyncMock(return_value=([], 0))

        with patch(
            "app.repositories.taoyuan.dispatch_order_repository.DispatchOrderRepository",
            return_value=mock_repo,
        ):
            result = await executor._search_dispatch_orders({"dispatch_no": "014"})
            mock_repo.filter_dispatch_orders.assert_called_once()
            call_kwargs = mock_repo.filter_dispatch_orders.call_args[1]
            assert call_kwargs["search"] == "014"

    @pytest.mark.asyncio
    async def test_search_strategy(self, executor):
        """策略 2: 關鍵字搜尋"""
        mock_repo = MagicMock()
        mock_repo.filter_dispatch_orders = AsyncMock(return_value=([], 0))

        with patch(
            "app.repositories.taoyuan.dispatch_order_repository.DispatchOrderRepository",
            return_value=mock_repo,
        ):
            result = await executor._search_dispatch_orders({"search": "道路工程"})
            call_kwargs = mock_repo.filter_dispatch_orders.call_args[1]
            assert call_kwargs["search"] == "道路工程"

    @pytest.mark.asyncio
    async def test_limit_cap_20(self, executor):
        """limit 上限 20"""
        mock_repo = MagicMock()
        mock_repo.filter_dispatch_orders = AsyncMock(return_value=([], 0))

        with patch(
            "app.repositories.taoyuan.dispatch_order_repository.DispatchOrderRepository",
            return_value=mock_repo,
        ):
            await executor._search_dispatch_orders({"search": "test", "limit": 100})
            call_kwargs = mock_repo.filter_dispatch_orders.call_args[1]
            assert call_kwargs["limit"] == 20
