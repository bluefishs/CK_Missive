"""
graph_helpers 圖譜工具函數單元測試

測試範圍：
- _clean_agency_name: 機關名稱清理
- _normalize_for_match: 名稱正規化
- _names_overlap: 雙向 includes 比對
- _extract_district: 行政區域提取
"""

import pytest

from app.services.ai.graph.graph_helpers import (
    _clean_agency_name,
    _normalize_for_match,
    _names_overlap,
    _extract_district,
    _DISTRICT_RE,
    _DISTRICT_EXCLUDE,
    _ORG_SUFFIXES,
)


class TestCleanAgencyName:
    """清理機關名稱"""

    def test_plain_name(self):
        assert _clean_agency_name('桃園市政府工務局') == '桃園市政府工務局'

    def test_strip_whitespace(self):
        assert _clean_agency_name('  桃園市政府工務局  ') == '桃園市政府工務局'

    def test_remove_newline(self):
        assert _clean_agency_name('桃園市政府\n工務局') == '桃園市政府工務局'

    def test_remove_carriage_return(self):
        assert _clean_agency_name('桃園市政府\r\n工務局') == '桃園市政府工務局'

    def test_strip_tax_id_prefix_8_digits(self):
        assert _clean_agency_name('50819619 乾坤測繪科技有限公司') == '乾坤測繪科技有限公司'

    def test_alphanumeric_prefix_not_stripped(self):
        # _clean_agency_name only strips pure digit prefixes (8-10 digits)
        # Alphanumeric prefixes like 'EB50819619' are NOT stripped
        result = _clean_agency_name('EB50819619 乾坤測繪科技有限公司')
        assert result == 'EB50819619 乾坤測繪科技有限公司'

    def test_only_digits_returns_original(self):
        # 全數字，strip 後為空 → 回傳原始值
        assert _clean_agency_name('12345678') == '12345678'

    def test_empty_string(self):
        assert _clean_agency_name('') == ''


class TestNormalizeForMatch:
    """名稱正規化用於模糊比對"""

    def test_strip_whitespace(self):
        assert _normalize_for_match('桃園 市政府') == '桃園市政府'

    def test_remove_suffix_有限公司(self):
        assert _normalize_for_match('乾坤測繪科技有限公司') == '乾坤測繪科技'

    def test_remove_suffix_股份有限公司(self):
        assert _normalize_for_match('台灣積體電路股份有限公司') == '台灣積體電路'

    def test_remove_suffix_分局(self):
        assert _normalize_for_match('交通部公路局中區養護工程分局') == '交通部公路局中區養護工程'

    def test_remove_suffix_事務所(self):
        assert _normalize_for_match('大有國際不動產估價師聯合事務所') == '大有國際不動產估價師聯合'

    def test_no_suffix(self):
        assert _normalize_for_match('桃園市政府工務局') == '桃園市政府工務局'


class TestNamesOverlap:
    """雙向 includes 比對"""

    def test_exact_match_short(self):
        # 短名稱（< 4 字元）精確匹配
        assert _names_overlap('工務局', '工務局') is True

    def test_short_name_mismatch(self):
        assert _names_overlap('工務局', '地政局') is False

    def test_contains_with_good_ratio(self):
        # 「桃園市政府工務局」含「桃園市政府工務」且比例 > 60%
        assert _names_overlap('桃園市政府工務', '桃園市政府工務局') is True

    def test_insufficient_ratio_rejected(self):
        # 「工務局」正規化後長度太短，與長名差距太大
        # _normalize_for_match('工務局') = '工務局' (3 chars)
        # → len < 4 → 走精確匹配分支 → False
        assert _names_overlap('工務局', '桃園市政府工務局') is False

    def test_same_name(self):
        assert _names_overlap('桃園市政府工務局', '桃園市政府工務局') is True

    def test_completely_different(self):
        assert _names_overlap('台北市交通局', '高雄市衛生局') is False


class TestExtractDistrict:
    """行政區域提取"""

    def test_extract_district_from_address(self):
        assert _extract_district('桃園市中壢區中華路一段100號') == '中壢區'

    def test_extract_district_鄉(self):
        assert _extract_district('南投縣仁愛鄉力行產業道路') == '仁愛鄉'

    def test_extract_district_鎮(self):
        assert _extract_district('彰化縣和美鎮彰美路五段') == '和美鎮'

    def test_no_district_found(self):
        assert _extract_district('桃園市政府工務局') is None

    def test_exclude_遊樂區(self):
        assert _extract_district('九族文化遊樂區') is None

    def test_exclude_工業區(self):
        assert _extract_district('中壢工業區') is None

    def test_exclude_社區(self):
        assert _extract_district('某某社區') is None

    def test_strip_市_prefix(self):
        # 「市楊梅區」→ 「楊梅區」
        assert _extract_district('桃園市楊梅區新農街100號') == '楊梅區'

    def test_strip_縣_prefix(self):
        # 「縣仁愛鄉」→ 「仁愛鄉」(regex 先匹配到 "仁愛鄉")
        result = _extract_district('南投縣仁愛鄉某路')
        assert result == '仁愛鄉'


class TestConstants:
    """常數正確性"""

    def test_district_exclude_contains_expected(self):
        assert '遊樂區' in _DISTRICT_EXCLUDE
        assert '工業區' in _DISTRICT_EXCLUDE
        assert '社區' in _DISTRICT_EXCLUDE

    def test_org_suffixes_regex(self):
        assert _ORG_SUFFIXES.search('乾坤測繪科技有限公司') is not None
        assert _ORG_SUFFIXES.search('桃園市政府工務局') is None
