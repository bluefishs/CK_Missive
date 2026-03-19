"""
搜尋詞彙擴展器單元測試

測試範圍：
- expand_search_terms: 兩層搜尋詞彙擴展管道
- flatten_expansions: 擴展結果扁平化
- MIN_TERM_LENGTH / MAX_EXPANSIONS_PER_TERM 常數行為

共 7 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.search_entity_expander import (
    expand_search_terms,
    flatten_expansions,
    MIN_TERM_LENGTH,
    MAX_EXPANSIONS_PER_TERM,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


# ============================================================================
# expand_search_terms
# ============================================================================

class TestExpandSearchTerms:
    """搜尋詞彙擴展"""

    @pytest.mark.asyncio
    async def test_empty_terms(self, mock_db):
        """空詞彙列表回傳空字典"""
        result = await expand_search_terms(mock_db, [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_self_included_in_expansions(self, mock_db):
        """原始詞必定包含在擴展結果中"""
        with patch(
            "app.services.ai.synonym_expander.SynonymExpander"
        ) as MockExpander:
            MockExpander.expand_keywords.return_value = ["工務局"]
            MockExpander.find_synonyms.return_value = []

            # Mock knowledge graph layer returns no results
            empty_result = MagicMock()
            empty_result.all.return_value = []
            mock_db.execute.return_value = empty_result

            result = await expand_search_terms(mock_db, ["工務局"])

        assert "工務局" in result
        assert "工務局" in result["工務局"]

    @pytest.mark.asyncio
    async def test_knowledge_graph_expansion(self, mock_db):
        """知識圖譜層擴展（別名/正規名稱）"""
        with patch(
            "app.services.ai.synonym_expander.SynonymExpander"
        ) as MockExpander:
            MockExpander.expand_keywords.return_value = ["桃園市政府"]
            MockExpander.find_synonyms.return_value = []

            # 模擬 Layer 2: 別名匹配 → canonical_id = 10
            alias_result = MagicMock()
            alias_result.all.return_value = [(10,)]

            # canonical 名稱匹配
            canon_result = MagicMock()
            canon_result.all.return_value = []

            # 別名展開
            aliases_result = MagicMock()
            aliases_result.all.return_value = [("桃市府",), ("桃園市府",)]

            # 正規名稱
            canon_names_result = MagicMock()
            canon_names_result.all.return_value = [("桃園市政府",)]

            mock_db.execute.side_effect = [
                alias_result,
                canon_result,
                aliases_result,
                canon_names_result,
            ]

            result = await expand_search_terms(mock_db, ["桃園市政府"])

        expansions = result["桃園市政府"]
        assert "桃園市政府" in expansions
        assert "桃市府" in expansions
        assert "桃園市府" in expansions

    @pytest.mark.asyncio
    async def test_short_term_skipped_in_knowledge_graph(self, mock_db):
        """短詞（< MIN_TERM_LENGTH）跳過知識圖譜擴展"""
        with patch(
            "app.services.ai.synonym_expander.SynonymExpander"
        ) as MockExpander:
            MockExpander.expand_keywords.return_value = ["A"]
            MockExpander.find_synonyms.return_value = []

            result = await expand_search_terms(mock_db, ["A"])

        # 不應執行 DB 查詢（知識圖譜層跳過）
        mock_db.execute.assert_not_called()
        assert result["A"] == {"A"}

    @pytest.mark.asyncio
    async def test_synonym_layer_failure_graceful(self, mock_db):
        """SynonymExpander 失敗時優雅降級"""
        with patch(
            "app.services.ai.synonym_expander.SynonymExpander",
            side_effect=ImportError("module not found"),
        ):
            empty_result = MagicMock()
            empty_result.all.return_value = []
            mock_db.execute.return_value = empty_result

            result = await expand_search_terms(mock_db, ["測試詞"])

        # 應有原始詞
        assert "測試詞" in result["測試詞"]


# ============================================================================
# flatten_expansions
# ============================================================================

class TestFlattenExpansions:
    """擴展結果扁平化"""

    def test_basic_flatten(self):
        """基本扁平化"""
        expansions = {
            "桃園市政府": {"桃園市政府", "桃市府"},
            "工務局": {"工務局", "工務處"},
        }
        result = flatten_expansions(expansions)

        assert "桃園市政府" in result
        assert "桃市府" in result
        assert "工務局" in result
        assert "工務處" in result
        # 原始詞在前
        assert result.index("桃園市政府") < result.index("桃市府")

    def test_deduplication(self):
        """去重（忽略大小寫）"""
        expansions = {
            "ABC": {"ABC", "abc", "DEF"},
        }
        result = flatten_expansions(expansions)

        # abc 和 ABC 只保留一個
        lower_counts = [r.lower() for r in result]
        assert lower_counts.count("abc") == 1
        assert "DEF" in result
