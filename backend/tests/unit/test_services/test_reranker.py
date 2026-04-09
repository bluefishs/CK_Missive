"""
重排序服務單元測試

測試範圍：
- compute_keyword_score: 關鍵字覆蓋度分數計算
- build_doc_text: 公文欄位合併
- rerank_documents: 混合重排序
- llm_rerank: LLM 批次重排序

共 7 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.ai.search.reranker import (
    compute_keyword_score,
    build_doc_text,
    rerank_documents,
    llm_rerank,
    STOPWORDS,
)


# ============================================================================
# compute_keyword_score
# ============================================================================

class TestComputeKeywordScore:
    """關鍵字覆蓋度分數"""

    def test_exact_match(self):
        """精確匹配得滿分"""
        score = compute_keyword_score(["道路改善工程"], "道路改善工程施工計畫")
        assert score > 0.8

    def test_no_match(self):
        """完全不匹配得零分"""
        score = compute_keyword_score(["土地查估"], "橋梁維修報告")
        assert score == 0.0

    def test_stopwords_filtered(self):
        """停用詞被過濾，不計分"""
        score = compute_keyword_score(["的", "了", "是"], "測試文件的內容")
        assert score == 0.0

    def test_empty_inputs(self):
        """空輸入回傳 0"""
        assert compute_keyword_score([], "some text") == 0.0
        assert compute_keyword_score(["term"], "") == 0.0

    def test_partial_match_lower_score(self):
        """部分匹配分數低於精確匹配"""
        exact = compute_keyword_score(["道路改善"], "道路改善工程")
        partial = compute_keyword_score(["道路改善"], "公路建設工程")
        assert exact > partial


# ============================================================================
# build_doc_text
# ============================================================================

class TestBuildDocText:
    """公文欄位合併"""

    def test_combines_fields(self):
        """合併所有欄位"""
        doc = {
            "subject": "測試主旨",
            "doc_number": "桃工字第123號",
            "sender": "桃園市政府",
            "receiver": "乾坤測繪",
        }
        text = build_doc_text(doc)
        assert "測試主旨" in text
        assert "桃工字第123號" in text
        assert "桃園市政府" in text
        assert "乾坤測繪" in text

    def test_empty_fields_skipped(self):
        """空欄位不加入"""
        doc = {"subject": "主旨", "doc_number": "", "sender": None}
        text = build_doc_text(doc)
        assert "主旨" in text
        assert text.strip() == "主旨"


# ============================================================================
# rerank_documents
# ============================================================================

class TestRerankDocuments:
    """混合重排序"""

    def test_rerank_by_keyword_boost(self):
        """關鍵字匹配的文件排名上升"""
        documents = [
            {"subject": "橋梁維修", "similarity": 0.8},
            {"subject": "道路改善工程計畫", "similarity": 0.75},
        ]
        result = rerank_documents(documents, ["道路改善"])

        # 第二篇有關鍵字匹配，應排到前面
        assert result[0]["subject"] == "道路改善工程計畫"
        assert "rerank_score" in result[0]
        assert "keyword_score" in result[0]

    def test_empty_documents(self):
        """空文件列表回傳原列表"""
        result = rerank_documents([], ["test"])
        assert result == []


# ============================================================================
# llm_rerank
# ============================================================================

class TestLlmRerank:
    """LLM 批次重排序"""

    @pytest.mark.asyncio
    async def test_single_document(self):
        """只有一篇時直接回傳"""
        docs = [{"subject": "唯一文件", "doc_number": "001"}]
        result = await llm_rerank(None, "問題", docs, top_n=5)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_rerank_success(self):
        """LLM 成功排序"""
        mock_connector = AsyncMock()
        mock_connector.chat_completion = AsyncMock(return_value="2,1")

        docs = [
            {"subject": "文件A", "doc_number": "001", "sender": "A", "receiver": "B"},
            {"subject": "文件B", "doc_number": "002", "sender": "C", "receiver": "D"},
        ]

        result = await llm_rerank(mock_connector, "問題", docs, top_n=2)

        assert len(result) == 2
        # LLM 回傳 "2,1"，所以第二篇排第一
        assert result[0]["subject"] == "文件B"
        assert "llm_relevance" in result[0]

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self):
        """LLM 呼叫失敗時保持原排序"""
        mock_connector = AsyncMock()
        mock_connector.chat_completion = AsyncMock(side_effect=Exception("API error"))

        docs = [
            {"subject": "文件A", "doc_number": "001", "sender": "", "receiver": ""},
            {"subject": "文件B", "doc_number": "002", "sender": "", "receiver": ""},
        ]

        result = await llm_rerank(mock_connector, "問題", docs, top_n=2)

        assert len(result) == 2
        assert result[0]["subject"] == "文件A"  # 保持原順序
