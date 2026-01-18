# -*- coding: utf-8 -*-
"""
AgencyNameParser 單元測試

測試統一的機關名稱解析邏輯。
"""
import pytest
from app.services.base.validators import AgencyNameParser


class TestAgencyNameParserParse:
    """測試 parse 方法"""

    def test_parse_empty_string(self):
        """測試空字串"""
        result = AgencyNameParser.parse("")
        assert result == []

    def test_parse_none(self):
        """測試 None 值"""
        result = AgencyNameParser.parse(None)
        assert result == []

    def test_parse_whitespace_only(self):
        """測試只有空白"""
        result = AgencyNameParser.parse("   ")
        assert result == []

    def test_parse_simple_name(self):
        """測試純名稱格式"""
        result = AgencyNameParser.parse("桃園市政府")
        assert len(result) == 1
        assert result[0] == (None, "桃園市政府")

    def test_parse_code_with_parentheses(self):
        """測試代碼+括號格式：380110000G (桃園市政府工務局)"""
        result = AgencyNameParser.parse("380110000G (桃園市政府工務局)")
        assert len(result) == 1
        assert result[0][0] == "380110000G"
        assert result[0][1] == "桃園市政府工務局"

    def test_parse_code_with_chinese_parentheses(self):
        """測試代碼+中文括號格式：380110000G（桃園市政府工務局）"""
        result = AgencyNameParser.parse("380110000G（桃園市政府工務局）")
        assert len(result) == 1
        assert result[0][0] == "380110000G"
        assert result[0][1] == "桃園市政府工務局"

    def test_parse_code_with_space(self):
        """測試代碼+空白格式：380110000G 桃園市政府工務局"""
        result = AgencyNameParser.parse("380110000G 桃園市政府工務局")
        assert len(result) == 1
        assert result[0][0] == "380110000G"
        assert result[0][1] == "桃園市政府工務局"

    def test_parse_multiple_agencies(self):
        """測試多機關格式：A01 (機關A) | B02 (機關B)"""
        result = AgencyNameParser.parse("A01020100G (內政部國土管理署) | 376480000A (南投縣政府)")
        assert len(result) == 2
        assert result[0][0] == "A01020100G"
        assert result[0][1] == "內政部國土管理署"
        assert result[1][0] == "376480000A"
        assert result[1][1] == "南投縣政府"

    def test_parse_with_newline(self):
        """測試換行格式：代碼\\n(名稱)"""
        result = AgencyNameParser.parse("380110000G\n(桃園市政府)")
        assert len(result) == 1
        assert result[0][0] == "380110000G"
        assert result[0][1] == "桃園市政府"


class TestAgencyNameParserExtractNames:
    """測試 extract_names 方法"""

    def test_extract_names_simple(self):
        """測試提取單一名稱"""
        result = AgencyNameParser.extract_names("桃園市政府")
        assert result == ["桃園市政府"]

    def test_extract_names_with_code(self):
        """測試從代碼格式提取名稱"""
        result = AgencyNameParser.extract_names("380110000G (桃園市政府工務局)")
        assert result == ["桃園市政府工務局"]

    def test_extract_names_multiple(self):
        """測試提取多個名稱"""
        result = AgencyNameParser.extract_names("A01 (機關A) | B02 (機關B)")
        assert len(result) == 2
        assert "機關A" in result
        assert "機關B" in result

    def test_extract_names_empty(self):
        """測試空值"""
        result = AgencyNameParser.extract_names("")
        assert result == []


class TestAgencyNameParserExtractCodes:
    """測試 extract_codes 方法"""

    def test_extract_codes_with_code(self):
        """測試提取代碼"""
        result = AgencyNameParser.extract_codes("380110000G (桃園市政府工務局)")
        assert result == ["380110000G"]

    def test_extract_codes_no_code(self):
        """測試無代碼的情況"""
        result = AgencyNameParser.extract_codes("桃園市政府")
        assert result == []

    def test_extract_codes_multiple(self):
        """測試提取多個代碼"""
        result = AgencyNameParser.extract_codes("A01020100G (機關A) | 376480000A (機關B)")
        assert len(result) == 2
        assert "A01020100G" in result
        assert "376480000A" in result


class TestAgencyNameParserCleanName:
    """測試 clean_name 方法"""

    def test_clean_name_simple(self):
        """測試清理純名稱"""
        result = AgencyNameParser.clean_name("桃園市政府")
        assert result == "桃園市政府"

    def test_clean_name_with_code_suffix(self):
        """測試移除代碼後綴"""
        result = AgencyNameParser.clean_name("桃園市政府(10002)")
        assert result == "桃園市政府"

    def test_clean_name_with_code_prefix(self):
        """測試移除代碼前綴（使用標準機關代碼格式）"""
        # 使用完整的英數字代碼格式（5-15位英數字）
        result = AgencyNameParser.clean_name("A01020100G 內政部國土管理署")
        assert result == "內政部國土管理署"

    def test_clean_name_with_number_prefix(self):
        """測試移除數字前綴"""
        result = AgencyNameParser.clean_name("10002 桃園市政府")
        assert result == "桃園市政府"

    def test_clean_name_empty(self):
        """測試空值"""
        result = AgencyNameParser.clean_name("")
        assert result is None

    def test_clean_name_none(self):
        """測試 None"""
        result = AgencyNameParser.clean_name(None)
        assert result is None

    def test_clean_name_whitespace(self):
        """測試只有空白"""
        result = AgencyNameParser.clean_name("   ")
        assert result is None
