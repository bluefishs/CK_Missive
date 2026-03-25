"""
graph_query_service 圖譜查詢服務單元測試

測試範圍：
- GraphQueryService 初始化
- search_entities 搜尋邏輯
- get_entity_detail 快取與查詢
- get_graph_stats / get_top_entities
- entity_graph 圖譜資料建構
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.ai.graph_query_service import GraphQueryService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.scalar = AsyncMock()
    db.get = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    with patch("app.services.ai.graph_query_service.get_ai_config") as mock_config:
        config = MagicMock()
        config.kg_fuzzy_threshold = 0.6
        mock_config.return_value = config
        return GraphQueryService(mock_db)


class TestInit:
    """初始化測試"""

    def test_service_created(self, service, mock_db):
        assert service.db is mock_db

    def test_config_loaded(self, service):
        assert service._config is not None


class TestGetEntityDetail:
    """get_entity_detail 實體詳情查詢"""

    @pytest.mark.asyncio
    async def test_returns_cached_result(self, service):
        """快取命中時直接返回"""
        cached_data = json.dumps({"canonical_name": "工務局", "id": 1})
        with patch(
            "app.services.ai.graph_query_service._graph_cache.get",
            new_callable=AsyncMock,
            return_value=cached_data,
        ):
            result = await service.get_entity_detail(1)
            assert result["canonical_name"] == "工務局"

    @pytest.mark.asyncio
    async def test_returns_none_when_entity_not_found(self, service, mock_db):
        """實體不存在時返回 None"""
        with patch(
            "app.services.ai.graph_query_service._graph_cache.get",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch.object(
                service, '_get_entity_detail_uncached',
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await service.get_entity_detail(999)
                assert result is None


class TestGetGraphStats:
    """get_graph_stats 圖譜統計"""

    @pytest.mark.asyncio
    async def test_returns_stats(self, service, mock_db):
        """返回統計數據"""
        with patch(
            "app.services.ai.graph_query_service._graph_cache.get",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.ai.graph_query_service._graph_cache.set",
            new_callable=AsyncMock,
        ):
            # mock scalar for counts (7 calls)
            mock_db.scalar = AsyncMock(return_value=10)

            # mock execute — called twice:
            # 1st: type_distribution {entity_type: count}
            # 2nd: source_project_distribution {project: count}
            type_row = MagicMock()
            type_row.entity_type = "org"
            type_row.count = 5
            type_result = MagicMock()
            type_result.all.return_value = [type_row]

            proj_row = MagicMock()
            proj_row.project = "ck-missive"
            proj_row.count = 10
            proj_result = MagicMock()
            proj_result.all.return_value = [proj_row]

            mock_db.execute = AsyncMock(side_effect=[type_result, proj_result])

            result = await service.get_graph_stats()
            assert isinstance(result, dict)
            assert "total_entities" in result
            assert result["total_entities"] == 10


class TestGetTopEntities:
    """get_top_entities 高頻實體"""

    @pytest.mark.asyncio
    async def test_returns_list(self, service, mock_db):
        """返回排序後的實體列表"""
        with patch(
            "app.services.ai.graph_query_service._graph_cache.get",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.ai.graph_query_service._graph_cache.set",
            new_callable=AsyncMock,
        ):
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await service.get_top_entities(limit=10)
            assert isinstance(result, list)


class TestSearchEntities:
    """search_entities 搜尋實體"""

    @pytest.mark.asyncio
    async def test_search_returns_list(self, service, mock_db):
        """搜尋返回實體列表"""
        with patch(
            "app.services.ai.graph_query_service._graph_cache.get",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.ai.graph_query_service._graph_cache.set",
            new_callable=AsyncMock,
        ):
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await service.search_entities("工務局")
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_with_entity_type_filter(self, service, mock_db):
        """搜尋帶實體類型過濾"""
        with patch(
            "app.services.ai.graph_query_service._graph_cache.get",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.ai.graph_query_service._graph_cache.set",
            new_callable=AsyncMock,
        ):
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await service.search_entities("工務局", entity_type="org")
            assert isinstance(result, list)
