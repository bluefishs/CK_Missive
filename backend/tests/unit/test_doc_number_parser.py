# -*- coding: utf-8 -*-
"""doc_number_parser 單元測試"""
import pytest
from app.utils.doc_number_parser import clean_doc_number, parse_doc_numbers


class TestCleanDocNumber:
    def test_empty_string(self):
        assert clean_doc_number("") == ""

    def test_none_like(self):
        assert clean_doc_number("") == ""

    def test_strip_whitespace(self):
        assert clean_doc_number("  桃工用字第123號  ") == "桃工用字第123號"

    def test_strip_newlines(self):
        assert clean_doc_number("\n桃工用字第123號\n") == "桃工用字第123號"

    def test_remove_book_title_marks(self):
        assert clean_doc_number("「桃工用字第123號」") == "桃工用字第123號"

    def test_fullwidth_digits(self):
        assert clean_doc_number("桃工用字第１２３號") == "桃工用字第123號"

    def test_fullwidth_parentheses(self):
        assert clean_doc_number("第（１１２）號") == "第(112)號"

    def test_compress_whitespace(self):
        assert clean_doc_number("桃工   用字  第123號") == "桃工 用字 第123號"

    def test_combined_cleaning(self):
        result = clean_doc_number("  「桃工用字第１１２號」  ")
        assert result == "桃工用字第112號"


class TestParseDocNumbers:
    def test_empty_input(self):
        assert parse_doc_numbers("") == []
        assert parse_doc_numbers(None) == []

    def test_whitespace_only(self):
        assert parse_doc_numbers("   ") == []

    def test_single_number(self):
        result = parse_doc_numbers("桃工用字第1120021701號")
        assert result == ["桃工用字第1120021701號"]

    def test_newline_separated(self):
        result = parse_doc_numbers("桃工用字第001號\n桃工用字第002號")
        assert result == ["桃工用字第001號", "桃工用字第002號"]

    def test_semicolon_separated(self):
        result = parse_doc_numbers("桃工用字第001號；桃工用字第002號")
        assert result == ["桃工用字第001號", "桃工用字第002號"]

    def test_half_semicolon_separated(self):
        result = parse_doc_numbers("桃工用字第001號;桃工用字第002號")
        assert result == ["桃工用字第001號", "桃工用字第002號"]

    def test_enumeration_comma_separated(self):
        result = parse_doc_numbers("桃工用字第001號、桃工用字第002號")
        assert result == ["桃工用字第001號", "桃工用字第002號"]

    def test_dedup_preserves_order(self):
        result = parse_doc_numbers("桃工用字第001號\n桃工用字第002號\n桃工用字第001號")
        assert result == ["桃工用字第001號", "桃工用字第002號"]

    def test_cleans_each_number(self):
        result = parse_doc_numbers("「桃工用字第１號」\n桃工用字第２號")
        assert result == ["桃工用字第1號", "桃工用字第2號"]

    def test_skips_empty_lines(self):
        result = parse_doc_numbers("桃工用字第001號\n\n\n桃工用字第002號")
        assert result == ["桃工用字第001號", "桃工用字第002號"]

    def test_numeric_input(self):
        result = parse_doc_numbers(12345)
        assert result == ["12345"]

    def test_crlf_separated(self):
        result = parse_doc_numbers("桃工用字第001號\r\n桃工用字第002號")
        assert result == ["桃工用字第001號", "桃工用字第002號"]
