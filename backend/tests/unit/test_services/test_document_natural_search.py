# -*- coding: utf-8 -*-
"""
自然語言公文搜尋服務單元測試
Document Natural Search Service Unit Tests

測試 document_natural_search.py 的核心邏輯

執行方式:
    pytest tests/unit/test_services/test_document_natural_search.py -v
"""
import asyncio
import os
import sys
import time
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.ai.search.document_natural_search import (
    execute_natural_search,
    _parse_intent_safe,
    _expand_entities,
    _build_query,
    _fetch_attachments,
    _fetch_projects,
    _assemble_results,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_service():
    service = MagicMock()
    service.connector = MagicMock()
    return service


def _make_parsed_intent(**kwargs):
    """建立 mock ParsedSearchIntent"""
    intent = MagicMock()
    intent.keywords = kwargs.get("keywords", ["測試"])
    intent.confidence = kwargs.get("confidence", 0.8)
    intent.doc_type = kwargs.get("doc_type", None)
    intent.category = kwargs.get("category", None)
    intent.sender = kwargs.get("sender", None)
    intent.receiver = kwargs.get("receiver", None)
    intent.date_from = kwargs.get("date_from", None)
    intent.date_to = kwargs.get("date_to", None)
    intent.status = kwargs.get("status", None)
    intent.contract_case = kwargs.get("contract_case", None)
    intent.related_entity = kwargs.get("related_entity", None)
    intent.model_dump = MagicMock(return_value={"keywords": intent.keywords})
    return intent


def _make_mock_document(doc_id=1, subject="測試公文"):
    doc = MagicMock()
    doc.id = doc_id
    doc.auto_serial = f"2026-{doc_id:04d}"
    doc.doc_number = f"乾字第{doc_id:04d}號"
    doc.subject = subject
    doc.doc_type = "收文"
    doc.category = "一般"
    doc.sender = "桃園市政府"
    doc.receiver = "乾坤測繪"
    doc.doc_date = date(2026, 3, 25)
    doc.status = "處理中"
    doc.contract_project_id = None
    doc.ck_note = None
    doc.created_at = datetime(2026, 3, 25, 10, 0, 0)
    doc.updated_at = datetime(2026, 3, 25, 10, 0, 0)
    return doc


# ============================================================================
# _parse_intent_safe 測試
# ============================================================================

class TestParseIntentSafe:
    """意圖解析安全包裝"""

    @pytest.mark.asyncio
    async def test_normal_parse(self, mock_service, mock_db):
        expected_intent = _make_parsed_intent(keywords=["公文"])
        mock_service.parse_search_intent = AsyncMock(return_value=(expected_intent, "llm"))

        intent, source = await _parse_intent_safe(mock_service, "找公文", mock_db)

        assert intent == expected_intent
        assert source == "llm"

    @pytest.mark.asyncio
    async def test_timeout_fallback(self, mock_service, mock_db):
        """超時應降級為關鍵字搜尋"""
        async def slow_parse(*args, **kwargs):
            await asyncio.sleep(20)

        mock_service.parse_search_intent = slow_parse

        with patch("app.services.ai.search.document_natural_search.asyncio.wait_for",
                    side_effect=asyncio.TimeoutError()):
            intent, source = await _parse_intent_safe(mock_service, "slow query", mock_db)

        assert source == "rule_engine"
        assert intent.confidence == 0.3

    @pytest.mark.asyncio
    async def test_exception_fallback(self, mock_service, mock_db):
        """異常應降級為關鍵字搜尋"""
        mock_service.parse_search_intent = AsyncMock(side_effect=RuntimeError("boom"))

        intent, source = await _parse_intent_safe(mock_service, "broken query", mock_db)

        assert source == "rule_engine"
        assert intent.confidence == 0.3


# ============================================================================
# _expand_entities 測試
# ============================================================================

class TestExpandEntities:
    """知識圖譜實體擴展"""

    @pytest.mark.asyncio
    async def test_no_keywords(self, mock_db):
        expanded, expanded_list, result_kw = await _expand_entities(mock_db, None)
        assert expanded is False
        assert result_kw == []

    @pytest.mark.asyncio
    async def test_empty_keywords(self, mock_db):
        expanded, expanded_list, result_kw = await _expand_entities(mock_db, [])
        assert expanded is False

    @pytest.mark.asyncio
    @patch("app.services.ai.search.search_entity_expander.expand_search_terms")
    @patch("app.services.ai.search.search_entity_expander.flatten_expansions")
    async def test_successful_expansion(self, mock_flatten, mock_expand, mock_db):
        mock_expand.return_value = {"桃園": ["桃園市政府", "桃園市"]}
        mock_flatten.return_value = ["桃園", "桃園市政府", "桃園市"]

        expanded, expanded_list, result_kw = await _expand_entities(mock_db, ["桃園"])

        assert expanded is True
        assert len(result_kw) == 3

    @pytest.mark.asyncio
    @patch("app.services.ai.search.search_entity_expander.expand_search_terms", side_effect=ImportError("module not found"))
    async def test_expansion_error_graceful(self, mock_expand, mock_db):
        """擴展失敗應不影響流程"""
        expanded, expanded_list, result_kw = await _expand_entities(mock_db, ["桃園"])

        assert expanded is False
        assert result_kw == ["桃園"]


# ============================================================================
# _build_query 測試
# ============================================================================

class TestBuildQuery:
    """查詢建構"""

    @patch("app.repositories.query_builders.document_query_builder.DocumentQueryBuilder")
    def test_basic_keyword_query(self, MockQB, mock_db):
        mock_qb = MagicMock()
        mock_qb.with_keywords_full.return_value = mock_qb
        MockQB.return_value = mock_qb

        intent = _make_parsed_intent(keywords=["測試"])

        request = MagicMock()
        request.max_results = 20
        request.offset = 0

        result = _build_query(mock_db, intent, ["測試"], None, request)

        mock_qb.with_keywords_full.assert_called_once_with(["測試"])

    @patch("app.repositories.query_builders.document_query_builder.DocumentQueryBuilder")
    def test_query_with_filters(self, MockQB, mock_db):
        mock_qb = MagicMock()
        mock_qb.with_keywords_full.return_value = mock_qb
        mock_qb.with_doc_type.return_value = mock_qb
        mock_qb.with_sender_like.return_value = mock_qb
        mock_qb.with_date_range.return_value = mock_qb
        MockQB.return_value = mock_qb

        intent = _make_parsed_intent(
            keywords=["測量"],
            doc_type="收文",
            sender="桃園市政府",
            date_from="2026-01-01",
            date_to="2026-03-31",
        )

        request = MagicMock()
        request.max_results = 20
        request.offset = 0

        _build_query(mock_db, intent, ["測量"], None, request)

        mock_qb.with_doc_type.assert_called_once_with("收文")
        mock_qb.with_sender_like.assert_called_once_with("桃園市政府")
        mock_qb.with_date_range.assert_called_once()

    @patch("app.repositories.query_builders.document_query_builder.DocumentQueryBuilder")
    def test_query_with_invalid_date(self, MockQB, mock_db):
        mock_qb = MagicMock()
        mock_qb.with_keywords_full.return_value = mock_qb
        MockQB.return_value = mock_qb

        intent = _make_parsed_intent(
            keywords=["測試"],
            date_from="invalid-date",
        )

        request = MagicMock()
        request.max_results = 20
        request.offset = 0

        # 不應拋出異常
        _build_query(mock_db, intent, ["測試"], None, request)

    @patch("app.repositories.query_builders.document_query_builder.DocumentQueryBuilder")
    def test_rls_filter_for_non_admin(self, MockQB, mock_db):
        mock_qb = MagicMock()
        mock_qb.with_keywords_full.return_value = mock_qb
        mock_qb.with_assignee_access.return_value = mock_qb
        MockQB.return_value = mock_qb

        intent = _make_parsed_intent(keywords=["測試"])

        user = MagicMock()
        user.role = "user"
        user.full_name = "王小明"
        user.username = "wang"

        request = MagicMock()
        request.max_results = 20
        request.offset = 0

        _build_query(mock_db, intent, ["測試"], user, request)

        mock_qb.with_assignee_access.assert_called_once_with("王小明")

    @patch("app.repositories.query_builders.document_query_builder.DocumentQueryBuilder")
    def test_rls_skipped_for_admin(self, MockQB, mock_db):
        mock_qb = MagicMock()
        mock_qb.with_keywords_full.return_value = mock_qb
        MockQB.return_value = mock_qb

        intent = _make_parsed_intent(keywords=["測試"])

        admin_user = MagicMock()
        admin_user.role = "admin"
        admin_user.full_name = "Admin"

        request = MagicMock()
        request.max_results = 20
        request.offset = 0

        _build_query(mock_db, intent, ["測試"], admin_user, request)

        mock_qb.with_assignee_access.assert_not_called()


# ============================================================================
# _fetch_attachments 測試
# ============================================================================

class TestFetchAttachments:
    """附件取得"""

    @pytest.mark.asyncio
    async def test_no_doc_ids(self, mock_db):
        result = await _fetch_attachments(mock_db, [], True)
        assert result == {}

    @pytest.mark.asyncio
    async def test_include_false(self, mock_db):
        result = await _fetch_attachments(mock_db, [1, 2, 3], False)
        assert result == {1: [], 2: [], 3: []}

    @pytest.mark.asyncio
    async def test_with_attachments(self, mock_db):
        att1 = MagicMock()
        att1.document_id = 1
        att1.id = 10
        att1.file_name = "test.pdf"
        att1.original_name = "report.pdf"
        att1.file_size = 1024
        att1.mime_type = "application/pdf"
        att1.created_at = datetime(2026, 3, 25)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [att1]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _fetch_attachments(mock_db, [1, 2], True)

        assert len(result[1]) == 1
        assert len(result[2]) == 0


# ============================================================================
# _fetch_projects 測試
# ============================================================================

class TestFetchProjects:
    """專案名稱取得"""

    @pytest.mark.asyncio
    async def test_empty_ids(self, mock_db):
        result = await _fetch_projects(mock_db, [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_with_projects(self, mock_db):
        proj = MagicMock()
        proj.id = 1
        proj.project_name = "桃園測量案"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [proj]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _fetch_projects(mock_db, [1])
        assert result == {1: "桃園測量案"}


# ============================================================================
# _assemble_results 測試
# ============================================================================

class TestAssembleResults:
    """結果組裝"""

    def test_basic_assembly(self):
        docs = [_make_mock_document(1, "測試公文A"), _make_mock_document(2, "測試公文B")]
        att_map = {1: [], 2: []}
        proj_map = {}

        results = _assemble_results(docs, att_map, proj_map)

        assert len(results) == 2
        assert results[0].subject == "測試公文A"
        assert results[1].subject == "測試公文B"
        assert results[0].attachment_count == 0

    def test_with_project_linkage(self):
        doc = _make_mock_document(1, "有專案公文")
        doc.contract_project_id = 5
        att_map = {1: []}
        proj_map = {5: "桃園測量專案"}

        results = _assemble_results([doc], att_map, proj_map)

        assert results[0].contract_project_name == "桃園測量專案"

    def test_empty_documents(self):
        results = _assemble_results([], {}, {})
        assert results == []


# ============================================================================
# execute_natural_search 整合測試
# ============================================================================

class TestExecuteNaturalSearch:
    """端對端整合測試"""

    @pytest.mark.asyncio
    @patch("app.services.ai.search.document_natural_search._write_search_history", new_callable=AsyncMock, return_value=1)
    @patch("app.services.ai.search.document_natural_search.resolve_search_entities", new_callable=AsyncMock, return_value=[])
    @patch("app.services.ai.search.document_natural_search._resolve_embedding", new_callable=AsyncMock, return_value=None)
    @patch("app.services.ai.search.document_natural_search._expand_entities", new_callable=AsyncMock, return_value=(False, None, ["測試"]))
    @patch("app.services.ai.search.document_natural_search._parse_intent_safe")
    async def test_full_pipeline_success(
        self, mock_parse, mock_expand, mock_embedding, mock_resolve, mock_history,
        mock_db, mock_service,
    ):
        intent = _make_parsed_intent(keywords=["測試"])
        mock_parse.return_value = (intent, "llm")

        docs = [_make_mock_document(1, "測試公文")]
        mock_qb = MagicMock()
        mock_qb.offset.return_value = mock_qb
        mock_qb.limit.return_value = mock_qb
        mock_qb.execute_with_count = AsyncMock(return_value=(docs, 1))

        with patch("app.services.ai.search.document_natural_search._build_query", return_value=mock_qb):
            with patch("app.services.ai.search.document_natural_search._fetch_attachments",
                        new_callable=AsyncMock, return_value={1: []}):
                with patch("app.services.ai.search.document_natural_search._fetch_projects",
                            new_callable=AsyncMock, return_value={}):
                    from app.schemas.ai.search import NaturalSearchRequest
                    request = MagicMock(spec=NaturalSearchRequest)
                    request.query = "測試搜尋"
                    request.max_results = 20
                    request.offset = 0
                    request.include_attachments = True

                    result = await execute_natural_search(mock_service, mock_db, request)

        assert result.success is True
        assert result.total == 1
        assert len(result.results) == 1

    @pytest.mark.asyncio
    @patch("app.services.ai.search.document_natural_search._expand_entities", new_callable=AsyncMock, return_value=(False, None, ["超時"]))
    @patch("app.services.ai.search.document_natural_search._parse_intent_safe")
    async def test_query_timeout_returns_error(self, mock_parse, mock_expand, mock_db, mock_service):
        intent = _make_parsed_intent(keywords=["超時"])
        mock_parse.return_value = (intent, "llm")

        mock_qb = MagicMock()
        mock_qb.offset.return_value = mock_qb
        mock_qb.limit.return_value = mock_qb

        with patch("app.services.ai.search.document_natural_search._build_query", return_value=mock_qb):
            with patch("app.services.ai.search.document_natural_search._resolve_embedding",
                        new_callable=AsyncMock, return_value=None):
                with patch("app.services.ai.search.document_natural_search.asyncio.wait_for",
                            side_effect=asyncio.TimeoutError()):
                    from app.schemas.ai.search import NaturalSearchRequest
                    request = MagicMock(spec=NaturalSearchRequest)
                    request.query = "timeout query"
                    request.max_results = 20
                    request.offset = 0
                    request.include_attachments = False

                    result = await execute_natural_search(mock_service, mock_db, request)

        assert result.success is False
        assert "超時" in result.error
