"""
知識圖譜入圖管線單元測試

測試範圍：
- ingest_document: 單篇公文入圖（含跳過/新建/合併）
- batch_ingest: 批次入圖
- 已入圖跳過邏輯
- 無實體跳過邏輯
- 關係正規化

共 7 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.ai.graph_ingestion_pipeline import GraphIngestionPipeline


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    db.scalar = AsyncMock()
    db.get = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    with patch(
        "app.services.ai.graph_ingestion_pipeline.CanonicalEntityService"
    ), patch(
        "app.services.ai.graph_ingestion_pipeline.get_ai_config"
    ) as mock_config:
        mock_config.return_value = MagicMock(ner_min_confidence=0.5)
        svc = GraphIngestionPipeline(mock_db)
        svc._entity_service = AsyncMock()
        return svc


# ============================================================================
# ingest_document - skip already ingested
# ============================================================================

class TestIngestDocumentSkip:
    """入圖跳過邏輯"""

    @pytest.mark.asyncio
    async def test_skip_already_ingested(self, service, mock_db):
        """已入圖的公文回傳 skipped"""
        mock_db.scalar.return_value = 1  # existing count > 0

        result = await service.ingest_document(document_id=1, force=False)

        assert result["status"] == "skipped"
        assert result["reason"] == "already_ingested"

    @pytest.mark.asyncio
    async def test_force_bypasses_check(self, service, mock_db):
        """force=True 跳過已入圖檢查"""
        # No entities found → should return skipped/no_entities, not already_ingested
        entities_result = MagicMock()
        entities_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = entities_result

        result = await service.ingest_document(document_id=1, force=True)

        assert result["status"] == "skipped"
        assert result["reason"] == "no_entities"


# ============================================================================
# ingest_document - no entities
# ============================================================================

class TestIngestDocumentNoEntities:
    """無實體跳過"""

    @pytest.mark.asyncio
    async def test_no_entities_skipped(self, service, mock_db):
        """無提取實體時跳過並記錄事件"""
        mock_db.scalar.return_value = 0  # not ingested yet

        entities_result = MagicMock()
        entities_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = entities_result

        result = await service.ingest_document(document_id=1)

        assert result["status"] == "skipped"
        assert result["reason"] == "no_entities"
        mock_db.add.assert_called_once()  # GraphIngestionEvent added


# ============================================================================
# ingest_document - full flow
# ============================================================================

class TestIngestDocumentFullFlow:
    """完整入圖流程"""

    @pytest.mark.asyncio
    async def test_successful_ingestion(self, service, mock_db):
        """成功入圖：實體正規化 + 關係建立"""
        mock_db.scalar.return_value = 0  # not ingested

        # Mock raw entities
        entity1 = MagicMock()
        entity1.entity_name = "桃園市政府"
        entity1.entity_type = "ORG"
        entity1.confidence = 0.9
        entity1.context = "公文內容"

        entity2 = MagicMock()
        entity2.entity_name = "道路改善"
        entity2.entity_type = "PROJECT"
        entity2.confidence = 0.8
        entity2.context = "工程案件"

        entities_result = MagicMock()
        entities_result.scalars.return_value.all.return_value = [entity1, entity2]

        # Mock relations
        relation1 = MagicMock()
        relation1.source_entity_name = "桃園市政府"
        relation1.source_entity_type = "ORG"
        relation1.target_entity_name = "道路改善"
        relation1.target_entity_type = "PROJECT"
        relation1.relation_type = "委辦"
        relation1.relation_label = "委辦關係"
        relation1.confidence = 0.85

        relations_result = MagicMock()
        relations_result.scalars.return_value.all.return_value = [relation1]

        # existing relationships lookup
        existing_rels_result = MagicMock()
        existing_rels_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            entities_result,
            relations_result,
            existing_rels_result,
        ]

        # Mock canonical entities
        canonical1 = MagicMock(id=100, mention_count=0)
        canonical2 = MagicMock(id=101, mention_count=0)
        service._entity_service.resolve_entities_batch = AsyncMock(
            return_value={
                "ORG:桃園市政府": canonical1,
                "PROJECT:道路改善": canonical2,
            }
        )
        service._entity_service.add_mention = AsyncMock()

        # Mock document for valid_from
        mock_doc = MagicMock()
        mock_doc.doc_date = None
        mock_db.get.return_value = mock_doc

        result = await service.ingest_document(document_id=42)

        assert result["status"] == "completed"
        assert result["entities_found"] == 2
        assert result["entities_new"] == 2
        assert result["relations_found"] == 1
        assert result["document_id"] == 42


# ============================================================================
# batch_ingest
# ============================================================================

class TestBatchIngest:
    """批次入圖"""

    @pytest.mark.asyncio
    async def test_no_pending_documents(self, service, mock_db):
        """無待入圖公文"""
        result_mock = MagicMock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        result = await service.batch_ingest(limit=50)

        assert result["status"] == "completed"
        assert result["total_processed"] == 0
        assert result["message"] == "無待入圖公文"

    @pytest.mark.asyncio
    async def test_batch_processes_documents(self, service, mock_db):
        """批次處理多篇公文"""
        result_mock = MagicMock()
        result_mock.all.return_value = [(1,), (2,), (3,)]
        mock_db.execute.return_value = result_mock

        # Mock begin_nested as async context manager
        mock_db.begin_nested = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(),
                __aexit__=AsyncMock(),
            )
        )

        # Mock ingest_document to return completed
        with patch.object(
            service, "ingest_document",
            new_callable=AsyncMock,
            return_value={"status": "completed"},
        ):
            result = await service.batch_ingest(limit=50)

        assert result["total_processed"] == 3
        assert result["success_count"] == 3
        assert result["error_count"] == 0

    @pytest.mark.asyncio
    async def test_batch_handles_errors(self, service, mock_db):
        """批次入圖中單篇失敗不影響整體"""
        result_mock = MagicMock()
        result_mock.all.return_value = [(1,), (2,)]
        mock_db.execute.return_value = result_mock

        mock_db.begin_nested = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(),
                __aexit__=AsyncMock(side_effect=[None, Exception("DB error")]),
            )
        )

        with patch.object(
            service, "ingest_document",
            new_callable=AsyncMock,
            side_effect=[{"status": "completed"}, Exception("fail")],
        ):
            result = await service.batch_ingest(limit=50)

        assert result["total_processed"] == 2
        # First succeeds, second errors
        assert result["success_count"] >= 1
