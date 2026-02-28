"""
DocumentAnalysisService 單元測試

測試 AI 分析持久化服務的業務邏輯：
- get_or_analyze：快取命中/miss/force
- _run_analysis：LLM 結果持久化 + 部分失敗
- mark_document_stale
- compute_text_hash：過期偵測
- batch_analyze

@version 1.0.0
@date 2026-02-28
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.document_analysis_service import (
    DocumentAnalysisService,
    ANALYSIS_VERSION,
)
from app.extended.models import DocumentAIAnalysis, OfficialDocument


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_by_document_id = AsyncMock(return_value=None)
    repo.upsert = AsyncMock()
    repo.mark_stale = AsyncMock()
    repo.get_pending_documents = AsyncMock(return_value=[])
    repo.get_stats = AsyncMock(return_value={
        "total_documents": 100,
        "analyzed_documents": 50,
        "stale_documents": 2,
        "without_analysis": 50,
        "coverage_percent": 50.0,
        "avg_processing_ms": 1200.0,
    })
    return repo


@pytest.fixture
def mock_ai_service():
    svc = AsyncMock()
    svc.generate_summary = AsyncMock(return_value={
        "summary": "測試摘要",
        "confidence": 0.9,
        "source": "groq",
        "model": "llama3-70b",
    })
    svc.suggest_classification = AsyncMock(return_value={
        "doc_type": "收文",
        "doc_type_confidence": 0.85,
        "category": "工程",
        "category_confidence": 0.8,
        "reasoning": "包含工程相關內容",
    })
    svc.extract_keywords = AsyncMock(return_value={
        "keywords": ["公文", "工程", "驗收"],
        "confidence": 0.88,
    })
    return svc


@pytest.fixture
def service(mock_db, mock_repo, mock_ai_service):
    with patch(
        "app.services.ai.document_analysis_service.get_document_ai_service",
        return_value=mock_ai_service,
    ):
        svc = DocumentAnalysisService(mock_db)
        svc.repo = mock_repo
        return svc


def _make_document(doc_id=1, subject="測試主旨", content="測試內容", sender="桃園市政府"):
    doc = MagicMock(spec=OfficialDocument)
    doc.id = doc_id
    doc.subject = subject
    doc.content = content
    doc.sender = sender
    return doc


def _make_analysis(
    doc_id=1,
    status="completed",
    is_stale=False,
    summary="摘要",
    source_text_hash=None,
):
    a = MagicMock(spec=DocumentAIAnalysis)
    a.id = 1
    a.document_id = doc_id
    a.status = status
    a.is_stale = is_stale
    a.summary = summary
    a.source_text_hash = source_text_hash
    a.entities_count = 0
    a.relations_count = 0
    return a


class TestGetOrAnalyze:
    """get_or_analyze 快取/分析邏輯"""

    @pytest.mark.asyncio
    async def test_cache_hit(self, service, mock_repo, mock_db):
        """已有完成的分析結果直接回傳（不呼叫 LLM）"""
        existing = _make_analysis(doc_id=1, status="completed")
        mock_repo.get_by_document_id.return_value = existing

        doc = _make_document(doc_id=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc
        mock_db.execute.return_value = mock_result

        # NER counts
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        mock_db.execute.side_effect = [mock_result, mock_count_result, mock_count_result]

        result = await service.get_or_analyze(1)

        assert result is not None
        mock_repo.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_triggers_analysis(self, service, mock_repo, mock_db):
        """無分析結果時觸發 LLM 分析"""
        mock_repo.get_by_document_id.return_value = None

        doc = _make_document(doc_id=1)
        new_analysis = _make_analysis(doc_id=1, status="completed")
        mock_repo.upsert.return_value = new_analysis

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_db.execute.side_effect = [mock_result, mock_count_result, mock_count_result]

        result = await service.get_or_analyze(1)

        assert result is not None
        mock_repo.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_triggers_reanalysis(self, service, mock_repo, mock_db):
        """force=True 即使有完成結果仍重新分析"""
        existing = _make_analysis(doc_id=1, status="completed")
        mock_repo.get_by_document_id.return_value = existing

        doc = _make_document(doc_id=1)
        new_analysis = _make_analysis(doc_id=1, status="completed")
        mock_repo.upsert.return_value = new_analysis

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_db.execute.side_effect = [mock_result, mock_count_result, mock_count_result]

        result = await service.get_or_analyze(1, force=True)

        mock_repo.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_stale_triggers_reanalysis(self, service, mock_repo, mock_db):
        """is_stale=True 觸發重新分析"""
        existing = _make_analysis(doc_id=1, status="completed", is_stale=True)
        mock_repo.get_by_document_id.return_value = existing

        doc = _make_document(doc_id=1)
        new_analysis = _make_analysis(doc_id=1, status="completed")
        mock_repo.upsert.return_value = new_analysis

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_db.execute.side_effect = [mock_result, mock_count_result, mock_count_result]

        result = await service.get_or_analyze(1)

        mock_repo.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_document_not_found_raises(self, service, mock_db):
        """公文不存在時拋出 NotFoundException"""
        from app.core.exceptions import NotFoundException

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundException):
            await service.get_or_analyze(999)


class TestRunAnalysis:
    """_run_analysis 內部邏輯"""

    @pytest.mark.asyncio
    async def test_all_succeed_status_completed(self, service, mock_repo, mock_db, mock_ai_service):
        """三項分析全成功 → status=completed"""
        doc = _make_document()
        new_analysis = _make_analysis(status="completed")
        mock_repo.upsert.return_value = new_analysis

        await service._run_analysis(doc)

        call_kwargs = mock_repo.upsert.call_args[1]
        assert call_kwargs["status"] == "completed"
        assert call_kwargs["summary"] == "測試摘要"
        assert call_kwargs["suggested_doc_type"] == "收文"
        assert call_kwargs["keywords"] == ["公文", "工程", "驗收"]
        assert call_kwargs["is_stale"] is False

    @pytest.mark.asyncio
    async def test_partial_failure_status_partial(self, service, mock_repo, mock_db, mock_ai_service):
        """部分失敗 → status=partial"""
        mock_ai_service.suggest_classification.side_effect = Exception("LLM 錯誤")

        doc = _make_document()
        new_analysis = _make_analysis(status="partial")
        mock_repo.upsert.return_value = new_analysis

        await service._run_analysis(doc)

        call_kwargs = mock_repo.upsert.call_args[1]
        assert call_kwargs["status"] == "partial"
        assert call_kwargs["summary"] == "測試摘要"
        assert call_kwargs["suggested_doc_type"] is None

    @pytest.mark.asyncio
    async def test_all_fail_status_failed(self, service, mock_repo, mock_db, mock_ai_service):
        """全部失敗 → status=failed"""
        mock_ai_service.generate_summary.side_effect = Exception("error")
        mock_ai_service.suggest_classification.side_effect = Exception("error")
        mock_ai_service.extract_keywords.side_effect = Exception("error")

        doc = _make_document()
        new_analysis = _make_analysis(status="failed")
        mock_repo.upsert.return_value = new_analysis

        await service._run_analysis(doc)

        call_kwargs = mock_repo.upsert.call_args[1]
        assert call_kwargs["status"] == "failed"


class TestMarkDocumentStale:
    """mark_document_stale 測試"""

    @pytest.mark.asyncio
    async def test_delegates_to_repo(self, service, mock_repo):
        """委派至 repo.mark_stale"""
        await service.mark_document_stale(42)

        mock_repo.mark_stale.assert_called_once_with(42)


class TestComputeTextHash:
    """compute_text_hash 雜湊計算"""

    def test_deterministic(self):
        """同樣輸入產生同樣 hash"""
        h1 = DocumentAnalysisService.compute_text_hash("主旨", "內容", "來源")
        h2 = DocumentAnalysisService.compute_text_hash("主旨", "內容", "來源")
        assert h1 == h2

    def test_different_input_different_hash(self):
        """不同輸入產生不同 hash"""
        h1 = DocumentAnalysisService.compute_text_hash("A", "B", "C")
        h2 = DocumentAnalysisService.compute_text_hash("X", "Y", "Z")
        assert h1 != h2

    def test_none_handling(self):
        """None 值不報錯"""
        h = DocumentAnalysisService.compute_text_hash(None, None, None)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256

    def test_hash_is_sha256(self):
        """Hash 長度為 64（SHA256 hex）"""
        h = DocumentAnalysisService.compute_text_hash("test", "", "")
        assert len(h) == 64


class TestGetAnalysisStats:
    """get_analysis_stats 統計"""

    @pytest.mark.asyncio
    async def test_returns_stats(self, service, mock_repo):
        """回傳統計數據"""
        result = await service.get_analysis_stats()

        assert result["total_documents"] == 100
        assert result["coverage_percent"] == 50.0
        mock_repo.get_stats.assert_called_once()


class TestBatchAnalyze:
    """batch_analyze 批次分析"""

    @pytest.mark.asyncio
    async def test_empty_pending(self, service, mock_repo):
        """無待分析公文回傳 0"""
        mock_repo.get_pending_documents.return_value = []

        result = await service.batch_analyze(limit=10)

        assert result["processed"] == 0
        assert result["success"] == 0

    @pytest.mark.asyncio
    async def test_processes_documents(self, service, mock_repo, mock_db):
        """處理多筆公文"""
        mock_repo.get_pending_documents.return_value = [1, 2]

        doc1 = _make_document(doc_id=1, subject="A")
        doc2 = _make_document(doc_id=2, subject="B")
        analysis1 = _make_analysis(doc_id=1)
        analysis2 = _make_analysis(doc_id=2)

        mock_repo.upsert.side_effect = [analysis1, analysis2]

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = doc1
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = doc2
        mock_db.execute.side_effect = [mock_result1, mock_result2]

        result = await service.batch_analyze(limit=10)

        assert result["processed"] == 2
        assert result["success"] == 2
        assert result["error"] == 0

    @pytest.mark.asyncio
    async def test_skips_empty_documents(self, service, mock_repo, mock_db):
        """跳過無主旨/內容的公文"""
        mock_repo.get_pending_documents.return_value = [1]

        empty_doc = _make_document(doc_id=1, subject="", content="")
        # subject and content are both falsy via or check
        empty_doc.subject = ""
        empty_doc.content = ""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = empty_doc
        mock_db.execute.return_value = mock_result

        result = await service.batch_analyze(limit=10)

        assert result["processed"] == 1
        assert result["skip"] == 1
        mock_repo.upsert.assert_not_called()
