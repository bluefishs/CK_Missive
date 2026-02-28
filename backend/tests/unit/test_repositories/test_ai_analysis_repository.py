"""
AIAnalysisRepository 單元測試

測試 AI 分析結果 Repository 的 CRUD + upsert + mark_stale + stats。
使用 mock AsyncSession，不需要實際資料庫連線。

@version 1.0.0
@date 2026-02-28
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.extended.models import DocumentAIAnalysis


class TestAIAnalysisRepositoryGetByDocumentId:
    """get_by_document_id 測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AIAnalysisRepository(mock_db)

    @pytest.mark.asyncio
    async def test_found(self, repo, mock_db):
        """取得已存在的分析結果"""
        mock_analysis = MagicMock(spec=DocumentAIAnalysis)
        mock_analysis.document_id = 42
        mock_analysis.summary = "測試摘要"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_analysis
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_document_id(42)

        assert result is not None
        assert result.document_id == 42
        assert result.summary == "測試摘要"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found(self, repo, mock_db):
        """查詢不存在的分析結果回傳 None"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_document_id(999)

        assert result is None


class TestAIAnalysisRepositoryGetByDocumentIds:
    """get_by_document_ids 批次查詢測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AIAnalysisRepository(mock_db)

    @pytest.mark.asyncio
    async def test_empty_ids(self, repo, mock_db):
        """空列表直接回傳空字典"""
        result = await repo.get_by_document_ids([])

        assert result == {}
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_ids(self, repo, mock_db):
        """批次取得多筆分析"""
        mock_a1 = MagicMock(spec=DocumentAIAnalysis)
        mock_a1.document_id = 1
        mock_a2 = MagicMock(spec=DocumentAIAnalysis)
        mock_a2.document_id = 3

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_a1, mock_a2]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_document_ids([1, 2, 3])

        assert len(result) == 2
        assert 1 in result
        assert 3 in result
        assert 2 not in result


class TestAIAnalysisRepositoryUpsert:
    """upsert 建立或更新測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AIAnalysisRepository(mock_db)

    @pytest.mark.asyncio
    async def test_upsert_calls_execute_and_flush(self, repo, mock_db):
        """upsert 呼叫 execute + flush + 回查"""
        mock_analysis = MagicMock(spec=DocumentAIAnalysis)
        mock_analysis.document_id = 10
        mock_analysis.summary = "新摘要"

        mock_result_query = MagicMock()
        mock_result_query.scalar_one_or_none.return_value = mock_analysis
        # 第一次 execute: INSERT ON CONFLICT, 第二次: SELECT 回查
        mock_db.execute.side_effect = [MagicMock(), mock_result_query]

        result = await repo.upsert(
            document_id=10,
            summary="新摘要",
            status="completed",
        )

        assert result.document_id == 10
        assert result.summary == "新摘要"
        assert mock_db.execute.call_count == 2
        mock_db.flush.assert_called_once()


class TestAIAnalysisRepositoryMarkStale:
    """mark_stale / mark_stale_batch 測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AIAnalysisRepository(mock_db)

    @pytest.mark.asyncio
    async def test_mark_stale(self, repo, mock_db):
        """標記單一公文為過期"""
        await repo.mark_stale(42)

        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_stale_batch_empty(self, repo, mock_db):
        """空列表回傳 0"""
        result = await repo.mark_stale_batch([])

        assert result == 0
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_stale_batch(self, repo, mock_db):
        """批次標記多筆"""
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute.return_value = mock_result

        result = await repo.mark_stale_batch([1, 2, 3])

        assert result == 3
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()


class TestAIAnalysisRepositoryGetPendingDocuments:
    """get_pending_documents 測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AIAnalysisRepository(mock_db)

    @pytest.mark.asyncio
    async def test_returns_document_ids(self, repo, mock_db):
        """回傳待分析的公文 ID"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [100, 101, 102]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repo.get_pending_documents(limit=10)

        assert result == [100, 101, 102]


class TestAIAnalysisRepositoryGetStats:
    """get_stats 覆蓋率統計測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return AIAnalysisRepository(mock_db)

    @pytest.mark.asyncio
    async def test_stats_calculation(self, repo, mock_db):
        """統計計算正確"""
        # 第一次查詢：公文總數
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 100

        # 第二次查詢：分析統計
        mock_stats_row = MagicMock()
        mock_stats_row.analyzed = 80
        mock_stats_row.stale = 5
        mock_stats_row.avg_ms = 1500.123
        mock_stats_result = MagicMock()
        mock_stats_result.one.return_value = mock_stats_row

        mock_db.execute.side_effect = [mock_total_result, mock_stats_result]

        result = await repo.get_stats()

        assert result["total_documents"] == 100
        assert result["analyzed_documents"] == 80
        assert result["stale_documents"] == 5
        assert result["without_analysis"] == 20
        assert result["coverage_percent"] == 80.0
        assert result["avg_processing_ms"] == 1500.1

    @pytest.mark.asyncio
    async def test_stats_zero_documents(self, repo, mock_db):
        """零公文不除以零"""
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 0

        mock_stats_row = MagicMock()
        mock_stats_row.analyzed = 0
        mock_stats_row.stale = 0
        mock_stats_row.avg_ms = None
        mock_stats_result = MagicMock()
        mock_stats_result.one.return_value = mock_stats_row

        mock_db.execute.side_effect = [mock_total_result, mock_stats_result]

        result = await repo.get_stats()

        assert result["total_documents"] == 0
        assert result["coverage_percent"] == 0.0
        assert result["avg_processing_ms"] == 0
