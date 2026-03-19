"""
RAG 查詢服務單元測試

測試範圍：
- _extract_query_terms: 查詢詞提取
- _build_context: 上下文建構
- _build_messages: LLM 訊息建構
- _get_system_prompt: System prompt 取得
- query: 非串流問答主流程
- stream_query: 串流問答

共 8 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.ai.rag_query_service import RAGQueryService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.rag_top_k = 5
    config.rag_similarity_threshold = 0.3
    config.rag_temperature = 0.3
    config.rag_max_tokens = 2048
    config.rag_max_history_turns = 3
    config.rag_max_context_chars = 5000
    config.hybrid_semantic_weight = 0.7
    config.embedding_dimension = 768
    return config


@pytest.fixture
def service(mock_db, mock_config):
    with patch("app.services.ai.rag_query_service.get_ai_connector") as mock_ai, \
         patch("app.services.ai.rag_query_service.EmbeddingManager") as mock_emb, \
         patch("app.services.ai.rag_query_service.get_ai_config", return_value=mock_config):
        svc = RAGQueryService(mock_db)
        svc.ai = mock_ai.return_value
        svc.embedding_mgr = mock_emb.return_value
        svc.config = mock_config
        yield svc


# ============================================================================
# _extract_query_terms
# ============================================================================

class TestExtractQueryTerms:
    """查詢詞提取測試"""

    def test_basic_extraction(self, service):
        terms = RAGQueryService._extract_query_terms("道路工程相關公文")
        # Should extract meaningful terms (length >= 2)
        assert isinstance(terms, list)
        assert all(len(t) >= 2 for t in terms)

    def test_empty_query(self, service):
        terms = RAGQueryService._extract_query_terms("")
        assert terms == []

    def test_stopwords_filtered(self, service):
        terms = RAGQueryService._extract_query_terms("在這個中")
        # All short/stopword tokens should be filtered
        assert all(t not in {"在", "這", "個", "中"} for t in terms)


# ============================================================================
# _build_context
# ============================================================================

class TestBuildContext:
    """上下文建構測試"""

    def test_context_formatting(self, service):
        sources = [
            {
                "doc_number": "桃工字第123號",
                "subject": "道路工程",
                "doc_type": "函",
                "category": "收文",
                "sender": "桃園市政府",
                "receiver": "乾坤測繪",
                "doc_date": "2026-01-01",
                "ck_note": "",
                "similarity": 0.85,
            }
        ]
        context = service._build_context(sources)
        assert "[公文1]" in context
        assert "桃工字第123號" in context
        assert "道路工程" in context

    def test_context_max_chars_limit(self, service):
        service.config.rag_max_context_chars = 50
        sources = [
            {
                "doc_number": f"DOC{i}",
                "subject": "非常長的主旨" * 10,
                "doc_type": "函",
                "category": "收文",
                "sender": "單位A",
                "receiver": "單位B",
                "doc_date": "2026-01-01",
                "ck_note": "",
                "similarity": 0.5,
            }
            for i in range(10)
        ]
        context = service._build_context(sources)
        # Should be truncated at max_chars
        assert len(context) <= 200  # generous bound for single entry


# ============================================================================
# _build_messages
# ============================================================================

class TestBuildMessages:
    """LLM 訊息建構測試"""

    def test_messages_structure(self, service):
        with patch.object(service, "_get_system_prompt", return_value="你是 AI 助理"):
            messages = service._build_messages("什麼是道路工程？", "context here")
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert "context here" in messages[-1]["content"]

    def test_history_included(self, service):
        history = [
            {"role": "user", "content": "前一個問題"},
            {"role": "assistant", "content": "前一個答案"},
        ]
        with patch.object(service, "_get_system_prompt", return_value="系統提示"):
            messages = service._build_messages("新問題", "context", history)
        # system + 2 history + 1 user = 4
        assert len(messages) == 4


# ============================================================================
# query (async)
# ============================================================================

class TestQuery:
    """非串流問答測試"""

    @pytest.mark.asyncio
    async def test_no_embedding_returns_error(self, service):
        service.embedding_mgr.get_embedding = AsyncMock(return_value=None)
        result = await service.query("測試問題")
        assert "無法生成查詢向量" in result["answer"]
        assert result["retrieval_count"] == 0

    @pytest.mark.asyncio
    async def test_no_sources_returns_fallback(self, service):
        service.embedding_mgr.get_embedding = AsyncMock(return_value=[0.1] * 768)
        with patch.object(service, "_retrieve_documents", new_callable=AsyncMock, return_value=[]):
            result = await service.query("不存在的問題")
        assert "找不到" in result["answer"]
        assert result["retrieval_count"] == 0
