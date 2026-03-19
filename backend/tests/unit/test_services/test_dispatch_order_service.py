"""
派工單核心服務單元測試

測試範圍：
- _extract_core_identifiers: 核心辨識詞提取
- _score_document_relevance: 公文相關性評分
- sync_fields_to_dispatch_orders: 欄位同步
- get_dispatch_order: 取得派工單
- delete_dispatch_order: 刪除流程
- _sync_work_type_links: 作業類別同步

共 8 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.taoyuan.dispatch_order_service import DispatchOrderService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    with patch("app.services.taoyuan.dispatch_order_service.DispatchOrderRepository"):
        svc = DispatchOrderService(mock_db)
        svc.repository = AsyncMock()
        return svc


# ============================================================================
# _extract_core_identifiers (static)
# ============================================================================

class TestExtractCoreIdentifiers:
    """核心辨識詞提取測試"""

    def test_extract_dispatch_number(self):
        ids = DispatchOrderService._extract_core_identifiers("派工單013 龍岡路道路工程")
        assert "派工單013" in ids

    def test_extract_road_name(self):
        ids = DispatchOrderService._extract_core_identifiers("中壢區龍岡路段改善工程")
        assert any("龍岡路" in i for i in ids)

    def test_extract_district(self):
        ids = DispatchOrderService._extract_core_identifiers("中壢區道路工程")
        assert "中壢區" in ids

    def test_empty_name_returns_empty(self):
        ids = DispatchOrderService._extract_core_identifiers("")
        assert ids == []

    def test_extract_park_name(self):
        ids = DispatchOrderService._extract_core_identifiers("霄裡公園改建工程")
        assert "霄裡公園" in ids


# ============================================================================
# _score_document_relevance (classmethod)
# ============================================================================

class TestScoreDocumentRelevance:
    """公文相關性評分測試"""

    def test_dispatch_number_match_returns_1(self):
        doc = {"subject": "有關派工單013之道路改善"}
        score = DispatchOrderService._score_document_relevance(
            doc, ["派工單013", "龍岡路"]
        )
        assert score == 1.0

    def test_no_match_returns_0(self):
        doc = {"subject": "完全無關的公文"}
        score = DispatchOrderService._score_document_relevance(
            doc, ["龍岡路", "中壢區"]
        )
        assert score == 0.0

    def test_generic_contract_doc_returns_half(self):
        doc = {"subject": "115年度桃園市道路養護開口契約之契約書"}
        score = DispatchOrderService._score_document_relevance(
            doc, ["龍岡路"]
        )
        assert score == 0.5


# ============================================================================
# sync_fields_to_dispatch_orders
# ============================================================================

class TestSyncFields:
    """欄位同步測試"""

    @pytest.mark.asyncio
    async def test_empty_fields_returns_zero(self, service):
        result = await service.sync_fields_to_dispatch_orders(1, {})
        assert result == 0

    @pytest.mark.asyncio
    async def test_no_dispatch_ids_returns_zero(self, service):
        service.repository.get_dispatch_ids_by_project = AsyncMock(return_value=[])
        result = await service.sync_fields_to_dispatch_orders(1, {"case_handler": "張三"})
        assert result == 0


# ============================================================================
# get_dispatch_order
# ============================================================================

class TestGetDispatchOrder:
    """取得派工單測試"""

    @pytest.mark.asyncio
    async def test_with_relations(self, service):
        expected = MagicMock()
        service.repository.get_with_relations = AsyncMock(return_value=expected)
        result = await service.get_dispatch_order(1, with_relations=True)
        assert result == expected
        service.repository.get_with_relations.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_without_relations(self, service):
        expected = MagicMock()
        service.repository.get_by_id = AsyncMock(return_value=expected)
        result = await service.get_dispatch_order(1, with_relations=False)
        assert result == expected
        service.repository.get_by_id.assert_awaited_once_with(1)
