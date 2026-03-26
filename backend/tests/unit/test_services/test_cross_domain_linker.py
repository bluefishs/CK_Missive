# -*- coding: utf-8 -*-
"""
跨域實體連結服務單元測試
CrossDomainLinker Unit Tests

測試 cross_domain_linker.py 的 4 條橋接規則與工具方法

執行方式:
    pytest tests/unit/test_services/test_cross_domain_linker.py -v
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.ai.cross_domain_linker import (
    CrossDomainLinker,
    LinkResult,
    LinkingReport,
    CONTRACTOR_THRESHOLD,
    PROJECT_THRESHOLD,
)


# ============================================================================
# Fixtures
# ============================================================================

def _make_entity(entity_id, name, entity_type="org", source_project="ck-missive", **kwargs):
    e = MagicMock()
    e.id = entity_id
    e.canonical_name = name
    e.entity_type = entity_type
    e.source_project = source_project
    e.linked_agency_id = kwargs.get("linked_agency_id")
    e.external_meta = kwargs.get("external_meta")
    e.embedding = kwargs.get("embedding")
    return e


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def linker(mock_db):
    return CrossDomainLinker(mock_db)


# ============================================================================
# _extract_section_name 測試
# ============================================================================

class TestExtractSectionName:
    """段名擷取"""

    def test_standard_format(self):
        assert CrossDomainLinker._extract_section_name("桃園市桃園區大興段0001-0000") == "桃園市桃園區大興段"

    def test_no_number(self):
        assert CrossDomainLinker._extract_section_name("桃園市桃園區大興段") == "桃園市桃園區大興段"

    def test_no_match(self):
        assert CrossDomainLinker._extract_section_name("台北市信義路三號") is None

    def test_empty(self):
        assert CrossDomainLinker._extract_section_name("") is None


# ============================================================================
# _find_best_match 測試
# ============================================================================

class TestFindBestMatch:
    """模糊匹配"""

    @pytest.mark.asyncio
    async def test_empty_candidates(self, linker):
        result, score = await linker._find_best_match("test", [])
        assert result is None
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_empty_name(self, linker):
        result, score = await linker._find_best_match("", [_make_entity(1, "test")])
        assert result is None
        assert score == 0.0

    @pytest.mark.asyncio
    @patch("app.services.ai.cross_domain_linker.CanonicalEntityMatcher")
    async def test_exact_match(self, MockMatcher, linker):
        MockMatcher.compute_similarity.return_value = 1.0
        MockMatcher.is_false_fuzzy_match.return_value = False

        candidate = _make_entity(1, "桃園市政府")

        with patch.object(linker, "_semantic_fallback", new_callable=AsyncMock, return_value=None):
            result, score = await linker._find_best_match("桃園市政府", [candidate])

        assert result == candidate
        assert score == 1.0

    @pytest.mark.asyncio
    @patch("app.services.ai.cross_domain_linker.CanonicalEntityMatcher")
    async def test_false_match_rejected(self, MockMatcher, linker):
        MockMatcher.compute_similarity.return_value = 0.90
        MockMatcher.is_false_fuzzy_match.return_value = True

        candidate = _make_entity(1, "桃園市")

        with patch.object(linker, "_semantic_fallback", new_callable=AsyncMock, return_value=None):
            result, score = await linker._find_best_match("桃園", [candidate])

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ai.cross_domain_linker.CanonicalEntityMatcher")
    async def test_below_threshold(self, MockMatcher, linker):
        MockMatcher.compute_similarity.return_value = 0.50

        candidate = _make_entity(1, "完全不同")

        with patch.object(linker, "_semantic_fallback", new_callable=AsyncMock, return_value=None):
            result, score = await linker._find_best_match("測試", [candidate], threshold=0.85)

        assert result is None


# ============================================================================
# _create_relation_if_absent 測試
# ============================================================================

class TestCreateRelationIfAbsent:
    """關係建立（去重）"""

    @pytest.mark.asyncio
    async def test_creates_new_relation(self, linker, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        created = await linker._create_relation_if_absent(1, 2, "contracted_by", "ck-tunnel")

        assert created is True
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_existing_relation(self, linker, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 42  # existing ID
        mock_db.execute = AsyncMock(return_value=mock_result)

        created = await linker._create_relation_if_absent(1, 2, "contracted_by", "ck-tunnel")

        assert created is False
        mock_db.add.assert_not_called()


# ============================================================================
# link_after_contribution 測試
# ============================================================================

class TestLinkAfterContribution:
    """連結觸發"""

    @pytest.mark.asyncio
    async def test_tunnel_triggers_three_rules(self, linker):
        with patch.object(linker, "_rule_contractor_bridging", new_callable=AsyncMock) as mock_c, \
             patch.object(linker, "_rule_project_bridging", new_callable=AsyncMock) as mock_p, \
             patch.object(linker, "_rule_agency_bridging", new_callable=AsyncMock) as mock_a:
            report = await linker.link_after_contribution("ck-tunnel")

        mock_c.assert_awaited_once()
        mock_p.assert_awaited_once()
        mock_a.assert_awaited_once()
        assert isinstance(report, LinkingReport)

    @pytest.mark.asyncio
    async def test_lvrland_triggers_location_rule(self, linker):
        with patch.object(linker, "_rule_location_bridging", new_callable=AsyncMock) as mock_l, \
             patch.object(linker, "_rule_contractor_bridging", new_callable=AsyncMock) as mock_c:
            report = await linker.link_after_contribution("ck-lvrland")

        mock_l.assert_awaited_once()
        mock_c.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_project_no_rules(self, linker):
        report = await linker.link_after_contribution("ck-unknown")
        assert report.links_created == 0

    @pytest.mark.asyncio
    async def test_error_captured_in_report(self, linker):
        with patch.object(
            linker, "_rule_contractor_bridging",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB down"),
        ):
            report = await linker.link_after_contribution("ck-tunnel")

        assert len(report.errors) == 1
        assert "DB down" in report.errors[0]


# ============================================================================
# run_all_rules 測試
# ============================================================================

class TestRunAllRules:
    """全量掃描"""

    @pytest.mark.asyncio
    async def test_runs_all_four_rules(self, linker):
        with patch.object(linker, "_rule_contractor_bridging", new_callable=AsyncMock) as mock_c, \
             patch.object(linker, "_rule_location_bridging", new_callable=AsyncMock) as mock_l, \
             patch.object(linker, "_rule_project_bridging", new_callable=AsyncMock) as mock_p, \
             patch.object(linker, "_rule_agency_bridging", new_callable=AsyncMock) as mock_a:
            report = await linker.run_all_rules()

        mock_c.assert_awaited_once()
        mock_l.assert_awaited_once()
        mock_p.assert_awaited_once()
        mock_a.assert_awaited_once()
        assert isinstance(report, LinkingReport)
        assert report.processing_ms >= 0


# ============================================================================
# LinkResult / LinkingReport 資料結構
# ============================================================================

class TestDataClasses:
    """資料結構"""

    def test_link_result(self):
        lr = LinkResult(
            source_id=1, target_id=2,
            relation_type="contracted_by",
            source_name="A公司", target_name="B機關",
            similarity=0.92, bridge_type="contractor",
        )
        assert lr.source_id == 1
        assert lr.similarity == 0.92

    def test_linking_report_defaults(self):
        report = LinkingReport()
        assert report.links_created == 0
        assert report.links_skipped == 0
        assert report.details == []
        assert report.errors == []

    def test_linking_report_accumulation(self):
        report = LinkingReport()
        report.links_created = 5
        report.links_skipped = 3
        report.details.append(LinkResult(1, 2, "test", "A", "B", 0.9, "x"))
        assert len(report.details) == 1
