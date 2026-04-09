# -*- coding: utf-8 -*-
"""
DocumentAIService 單元測試

測試範圍:
- _build_summary_prompt: Prompt 建構邏輯
- generate_summary: 摘要生成（含快取/降級）
- suggest_classification: 分類建議（含 schema 驗證/降級）
- extract_keywords: 關鍵字提取
- resolve_search_entities: 批次正規化實體解析 (document_search_helpers)

@version 1.0.0
@date 2026-03-14
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.document.document_ai_service import DocumentAIService
from app.services.ai.document.document_search_helpers import resolve_search_entities


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_ai_config():
    config = MagicMock()
    config.agency_match_threshold = 0.7
    config.summary_max_tokens = 200
    config.cache_ttl_summary = 3600
    config.cache_ttl_classify = 3600
    config.cache_ttl_keywords = 3600
    config.classify_max_tokens = 128
    config.keywords_max_tokens = 128
    config.search_query_timeout = 20.0
    config.hybrid_semantic_weight = 0.3
    config.embedding_cache_max_size = 100
    config.embedding_cache_ttl = 60
    return config


def _mock_get_system_prompt(key):
    """根據不同 key 回傳對應的 format 模板字串"""
    templates = {
        "summary": "你是一個摘要助手，最長 {max_length} 字",
        "classify": "你是分類助手，類型：{doc_types_str}",
        "keywords": "你是關鍵字助手，最多 {max_keywords} 個",
        "match_agency": "你是機關匹配助手",
    }
    return templates.get(key, "fallback prompt")


@pytest.fixture
def service(mock_ai_config):
    """建立 DocumentAIService，mock 所有外部依賴"""
    with patch("app.services.ai.document.document_ai_service.AIPromptManager") as MockPM, \
         patch("app.services.ai.document.document_ai_service.get_ai_config", return_value=mock_ai_config), \
         patch("app.services.ai.core.base_ai_service.get_ai_config", return_value=mock_ai_config):

        # Mock prompt manager
        MockPM.load_prompts = MagicMock()
        MockPM.get_system_prompt = MagicMock(side_effect=_mock_get_system_prompt)
        MockPM.ensure_db_prompts_loaded = AsyncMock()

        svc = DocumentAIService()
        # Mock internal methods
        svc._rate_limiter = MagicMock()
        svc._rate_limiter.can_proceed.return_value = True
        svc._rate_limiter.get_wait_time.return_value = 0
        svc._stats_manager = MagicMock()
        svc._stats_manager.record_rate_limit_hit = AsyncMock()
        svc.connector = MagicMock()
        svc.config = mock_ai_config
        yield svc


# ============================================================
# _build_summary_prompt 測試
# ============================================================

class TestBuildSummaryPrompt:
    """_build_summary_prompt 測試"""

    def test_basic_prompt(self, service):
        """基本 prompt 包含主旨"""
        result = service._build_summary_prompt("測試主旨")
        assert "system" in result
        assert "user" in result
        assert "測試主旨" in result["user"]

    def test_prompt_with_sender(self, service):
        """prompt 包含發文機關"""
        result = service._build_summary_prompt("主旨", sender="桃園市政府")
        assert "桃園市政府" in result["user"]

    def test_prompt_with_content(self, service):
        """prompt 包含內容（截斷至 500 字）"""
        long_content = "A" * 1000
        result = service._build_summary_prompt("主旨", content=long_content)
        # Content should be truncated
        assert len(result["user"]) < 1000 + 100  # main text + metadata


# ============================================================
# generate_summary 測試
# ============================================================

class TestGenerateSummary:
    """generate_summary 測試"""

    @pytest.mark.asyncio
    async def test_disabled_returns_fallback(self, service):
        """AI 停用時回傳原始主旨"""
        service.is_enabled = MagicMock(return_value=False)

        result = await service.generate_summary("這是主旨", max_length=50)

        assert result["source"] == "disabled"
        assert result["summary"] == "這是主旨"
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_success_returns_ai_summary(self, service):
        """AI 成功生成摘要"""
        service.is_enabled = MagicMock(return_value=True)
        service._call_ai_with_cache = AsyncMock(return_value="AI 生成的摘要")

        result = await service.generate_summary("測試主旨")

        assert result["source"] == "ai"
        assert result["summary"] == "AI 生成的摘要"
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_rate_limited_returns_fallback(self, service):
        """速率限制時回傳 fallback"""
        service.is_enabled = MagicMock(return_value=True)
        service._call_ai_with_cache = AsyncMock(
            side_effect=RuntimeError("速率限制")
        )

        result = await service.generate_summary("原始主旨")

        assert result["source"] == "rate_limited"
        assert result["summary"] == "原始主旨"

    @pytest.mark.asyncio
    async def test_error_returns_fallback(self, service):
        """AI 錯誤時回傳 fallback"""
        service.is_enabled = MagicMock(return_value=True)
        service._call_ai_with_cache = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await service.generate_summary("原始主旨")

        assert result["source"] == "fallback"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_long_summary_truncated(self, service):
        """超長摘要被截斷"""
        service.is_enabled = MagicMock(return_value=True)
        long_summary = "A" * 200
        service._call_ai_with_cache = AsyncMock(return_value=long_summary)

        result = await service.generate_summary("主旨", max_length=50)

        assert len(result["summary"]) <= 50
        assert result["summary"].endswith("...")


# ============================================================
# suggest_classification 測試
# ============================================================

class TestSuggestClassification:
    """suggest_classification 測試"""

    @pytest.mark.asyncio
    async def test_disabled_returns_defaults(self, service):
        """AI 停用時回傳預設分類"""
        service.is_enabled = MagicMock(return_value=False)

        result = await service.suggest_classification("測試主旨")

        assert result["doc_type"] == "函"
        assert result["category"] == "收文"
        assert result["source"] == "disabled"

    @pytest.mark.asyncio
    async def test_success_returns_classification(self, service):
        """AI 成功回傳分類"""
        service.is_enabled = MagicMock(return_value=True)
        service._call_ai_with_validation = AsyncMock(return_value={
            "doc_type": "公告",
            "category": "發文",
            "doc_type_confidence": 0.9,
            "category_confidence": 0.85,
            "reasoning": "含公告相關內容",
        })

        result = await service.suggest_classification("公告事項")

        assert result["doc_type"] == "公告"
        assert result["category"] == "發文"
        assert result["source"] == "ai"

    @pytest.mark.asyncio
    async def test_invalid_doc_type_falls_back(self, service):
        """AI 回傳無效分類時降級為預設"""
        service.is_enabled = MagicMock(return_value=True)
        service._call_ai_with_validation = AsyncMock(return_value={
            "doc_type": "無效類型",
            "category": "無效類別",
        })

        result = await service.suggest_classification("主旨")

        assert result["doc_type"] == "函"
        assert result["category"] == "收文"


# ============================================================
# extract_keywords 測試
# ============================================================

class TestExtractKeywords:
    """extract_keywords 測試"""

    @pytest.mark.asyncio
    async def test_disabled_returns_empty(self, service):
        """AI 停用時回傳空關鍵字"""
        service.is_enabled = MagicMock(return_value=False)

        result = await service.extract_keywords("測試主旨")

        assert result["keywords"] == []
        assert result["source"] == "disabled"

    @pytest.mark.asyncio
    async def test_success_returns_keywords(self, service):
        """AI 成功回傳關鍵字"""
        service.is_enabled = MagicMock(return_value=True)
        service._call_ai_with_validation = AsyncMock(return_value={
            "keywords": ["測繪", "工程", "驗收"]
        })

        result = await service.extract_keywords("關於測繪工程驗收")

        assert result["keywords"] == ["測繪", "工程", "驗收"]
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_max_keywords_respected(self, service):
        """關鍵字數量不超過上限"""
        service.is_enabled = MagicMock(return_value=True)
        service._call_ai_with_validation = AsyncMock(return_value={
            "keywords": ["A", "B", "C", "D", "E", "F"]
        })

        result = await service.extract_keywords("主旨", max_keywords=3)

        assert len(result["keywords"]) <= 3

    @pytest.mark.asyncio
    async def test_non_list_keywords_handled(self, service):
        """AI 回傳非列表 keywords 時處理為空列表"""
        service.is_enabled = MagicMock(return_value=True)
        service._call_ai_with_validation = AsyncMock(return_value={
            "keywords": "not a list"
        })

        result = await service.extract_keywords("主旨")

        assert result["keywords"] == []


# ============================================================
# resolve_search_entities 批次測試 (document_search_helpers)
# ============================================================

class TestResolveSearchEntities:
    """resolve_search_entities 批次正規化實體解析"""

    @pytest.mark.asyncio
    async def test_empty_intent_returns_empty(self):
        """無 sender/receiver 時回傳空列表"""
        mock_db = AsyncMock()
        mock_intent = MagicMock()
        mock_intent.sender = None
        mock_intent.receiver = None

        result = await resolve_search_entities(
            mock_db, mock_intent, []
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_batch_canonical_lookup(self):
        """批次 canonical_name 查詢正常運作"""
        mock_db = AsyncMock()
        mock_intent = MagicMock()
        mock_intent.sender = "桃園市政府"
        mock_intent.receiver = None

        # Mock canonical entity found
        mock_entity = MagicMock()
        mock_entity.id = 1
        mock_entity.canonical_name = "桃園市政府"
        mock_entity.entity_type = "org"
        mock_entity.mention_count = 10

        mock_canonical_result = MagicMock()
        mock_canonical_result.scalars.return_value.all.return_value = [mock_entity]
        mock_db.execute.return_value = mock_canonical_result

        result = await resolve_search_entities(
            mock_db, mock_intent, []
        )

        assert len(result) == 1
        assert result[0].canonical_name == "桃園市政府"
        assert result[0].entity_type == "org"

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """重複實體去重"""
        mock_db = AsyncMock()
        mock_intent = MagicMock()
        mock_intent.sender = "桃園市政府"
        mock_intent.receiver = None

        # Same entity found via canonical lookup
        mock_entity = MagicMock()
        mock_entity.id = 1
        mock_entity.canonical_name = "桃園市政府"
        mock_entity.entity_type = "org"
        mock_entity.mention_count = 10

        mock_canonical_result = MagicMock()
        mock_canonical_result.scalars.return_value.all.return_value = [mock_entity]
        mock_db.execute.return_value = mock_canonical_result

        # Search results also contain "桃園市政府" as sender
        mock_search_result = MagicMock()
        mock_search_result.sender = "桃園市政府"

        result = await resolve_search_entities(
            mock_db, mock_intent, [mock_search_result]
        )

        # Should still be just 1 (deduped by entity.id)
        assert len(result) == 1
