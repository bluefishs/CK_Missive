"""
synonym_expander 同義詞擴展服務單元測試

測試範圍：
- SynonymExpander._build_lookup 索引建立
- SynonymExpander.expand_keywords 關鍵字擴展
- SynonymExpander._fuzzy_lookup 模糊查找
- SynonymExpander.expand_agency 機關縮寫轉全稱
- SynonymExpander.find_synonyms 同義詞查詢
- SynonymExpander.get_status_normalize 狀態正規化
- SynonymExpander.expand_search_terms 搜尋詞擴展
- SynonymExpander.reload_from_db DB 重建
- SynonymExpander.invalidate 快取清除
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.ai.search.synonym_expander import SynonymExpander


@pytest.fixture(autouse=True)
def reset_singleton():
    """每個測試前重置 Singleton 狀態"""
    original_lookup = SynonymExpander._lookup
    original_raw = SynonymExpander._raw_data
    yield
    SynonymExpander._lookup = original_lookup
    SynonymExpander._raw_data = original_raw


class TestBuildLookup:
    """_build_lookup 索引建立"""

    def test_empty_data(self):
        lookup = SynonymExpander._build_lookup({})
        assert lookup == {}

    def test_single_group(self):
        data = {"agencies": [["桃園市政府工務局", "工務局", "桃工"]]}
        lookup = SynonymExpander._build_lookup(data)
        assert "桃園市政府工務局" in lookup
        assert "工務局" in lookup
        assert "桃工" in lookup
        assert lookup["工務局"] == ["桃園市政府工務局", "工務局", "桃工"]

    def test_multiple_groups(self):
        data = {
            "agencies": [
                ["工務局", "桃工"],
                ["地政局", "桃地"],
            ]
        }
        lookup = SynonymExpander._build_lookup(data)
        assert lookup["工務局"] == ["工務局", "桃工"]
        assert lookup["地政局"] == ["地政局", "桃地"]

    def test_non_list_group_skipped(self):
        data = {"agencies": "not a list"}
        lookup = SynonymExpander._build_lookup(data)
        assert lookup == {}

    def test_non_list_item_skipped(self):
        data = {"agencies": ["not a list item", ["a", "b"]]}
        lookup = SynonymExpander._build_lookup(data)
        assert "a" in lookup
        assert "not a list item" not in lookup


class TestExpandKeywords:
    """expand_keywords 關鍵字擴展"""

    def test_no_synonyms(self):
        SynonymExpander._lookup = {}
        result = SynonymExpander.expand_keywords(["隨意詞彙"])
        assert result == ["隨意詞彙"]

    def test_exact_match_expansion(self):
        SynonymExpander._lookup = {
            "工務局": ["桃園市政府工務局", "工務局", "桃工"],
            "桃園市政府工務局": ["桃園市政府工務局", "工務局", "桃工"],
            "桃工": ["桃園市政府工務局", "工務局", "桃工"],
        }
        result = SynonymExpander.expand_keywords(["工務局"])
        assert "桃園市政府工務局" in result
        assert "工務局" in result
        assert "桃工" in result

    def test_deduplication(self):
        SynonymExpander._lookup = {
            "工務局": ["工務局", "桃工"],
            "桃工": ["工務局", "桃工"],
        }
        result = SynonymExpander.expand_keywords(["工務局", "桃工"])
        # 應去重
        assert len(result) == len(set(result))

    def test_fuzzy_match_when_no_exact(self):
        SynonymExpander._lookup = {
            "工務局": ["桃園市政府工務局", "工務局", "桃工"],
            "桃園市政府工務局": ["桃園市政府工務局", "工務局", "桃工"],
            "桃工": ["桃園市政府工務局", "工務局", "桃工"],
        }
        # 「桃園市工務局」contains「工務局」→ 模糊匹配命中
        result = SynonymExpander.expand_keywords(["桃園市工務局"])
        assert "桃園市政府工務局" in result

    def test_short_keyword_no_fuzzy(self):
        """短於 3 字元的關鍵字不觸發模糊匹配"""
        SynonymExpander._lookup = {
            "道路工程": ["道路工程", "路工"],
        }
        result = SynonymExpander.expand_keywords(["工"])
        # 短關鍵字不觸發模糊
        assert result == ["工"]


class TestFuzzyLookup:
    """_fuzzy_lookup 模糊查找"""

    def test_keyword_contains_term(self):
        lookup = {"工務局": ["工務局", "桃工"]}
        result = SynonymExpander._fuzzy_lookup("桃園市政府工務局", lookup)
        assert result == ["工務局", "桃工"]

    def test_term_contains_keyword(self):
        lookup = {"桃園市政府工務局": ["桃園市政府工務局", "桃工"]}
        result = SynonymExpander._fuzzy_lookup("工務局", lookup)
        assert result == ["桃園市政府工務局", "桃工"]

    def test_no_match(self):
        lookup = {"衛生局": ["衛生局", "衛生處"]}
        result = SynonymExpander._fuzzy_lookup("工務局", lookup)
        assert result is None

    def test_longest_match_preferred(self):
        lookup = {
            "工務": ["工務", "工"],
            "桃園市政府工務局": ["桃園市政府工務局", "桃工"],
        }
        result = SynonymExpander._fuzzy_lookup("桃園市政府工務局工程", lookup)
        # 應選最長匹配
        assert result == ["桃園市政府工務局", "桃工"]


class TestExpandAgency:
    """expand_agency 機關縮寫轉全稱"""

    def test_found_in_lookup(self):
        SynonymExpander._lookup = {
            "桃工": ["桃園市政府工務局", "桃工"],
        }
        result = SynonymExpander.expand_agency("桃工")
        assert result == "桃園市政府工務局"

    def test_not_found_returns_original(self):
        SynonymExpander._lookup = {}
        result = SynonymExpander.expand_agency("未知機關")
        assert result == "未知機關"


class TestFindSynonyms:
    """find_synonyms 同義詞查詢"""

    def test_found_excludes_self(self):
        SynonymExpander._lookup = {
            "工務局": ["桃園市政府工務局", "工務局", "桃工"],
        }
        result = SynonymExpander.find_synonyms("工務局")
        assert "工務局" not in result
        assert "桃園市政府工務局" in result
        assert "桃工" in result

    def test_not_found(self):
        SynonymExpander._lookup = {}
        result = SynonymExpander.find_synonyms("工務局")
        assert result == []


class TestExpandSearchTerms:
    """expand_search_terms 搜尋詞擴展"""

    def test_includes_original(self):
        SynonymExpander._lookup = {}
        result = SynonymExpander.expand_search_terms("工務局")
        assert "工務局" in result

    def test_includes_synonyms(self):
        SynonymExpander._lookup = {
            "工務局": ["桃園市政府工務局", "工務局", "桃工"],
        }
        result = SynonymExpander.expand_search_terms("工務局")
        assert "工務局" in result
        assert "桃園市政府工務局" in result
        assert "桃工" in result


class TestReloadFromDb:
    """reload_from_db DB 重建"""

    def test_builds_lookup_from_records(self):
        record1 = MagicMock()
        record1.words = "桃園市政府工務局,工務局,桃工"
        record2 = MagicMock()
        record2.words = "地政局,桃地"

        count = SynonymExpander.reload_from_db([record1, record2])
        assert count == 5
        assert SynonymExpander._lookup is not None
        assert "工務局" in SynonymExpander._lookup
        assert "桃地" in SynonymExpander._lookup

    def test_empty_records(self):
        count = SynonymExpander.reload_from_db([])
        assert count == 0


class TestInvalidate:
    """invalidate 快取清除"""

    def test_clears_lookup(self):
        SynonymExpander._lookup = {"test": ["test"]}
        SynonymExpander._raw_data = {"test": [["test"]]}
        SynonymExpander.invalidate()
        assert SynonymExpander._lookup is None
        assert SynonymExpander._raw_data is None


class TestGetStatusNormalize:
    """get_status_normalize 狀態正規化"""

    def test_returns_dict(self):
        SynonymExpander._lookup = {
            "待處理": ["待處理", "未處理", "尚未處理"],
            "未處理": ["待處理", "未處理", "尚未處理"],
            "尚未處理": ["待處理", "未處理", "尚未處理"],
        }
        result = SynonymExpander.get_status_normalize()
        assert isinstance(result, dict)
        assert result.get("未處理") == "待處理"
        assert result.get("尚未處理") == "待處理"

    def test_no_status_synonyms(self):
        SynonymExpander._lookup = {
            "工務局": ["工務局", "桃工"],
        }
        result = SynonymExpander.get_status_normalize()
        assert result == {}
