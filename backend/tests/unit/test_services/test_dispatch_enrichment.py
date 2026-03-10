# -*- coding: utf-8 -*-
"""dispatch_enrichment_service 純函數單元測試"""
import pytest
from datetime import date

from app.services.taoyuan.dispatch_enrichment_service import (
    parse_roc_date,
    parse_sequence_no,
    parse_amount,
    safe_cell,
    parse_doc_line,
)


class TestParseRocDate:
    def test_standard_date(self):
        assert parse_roc_date("112.7.14") == date(2023, 7, 14)

    def test_zero_padded(self):
        assert parse_roc_date("112.07.14") == date(2023, 7, 14)

    def test_three_digit_year(self):
        assert parse_roc_date("113.5.2") == date(2024, 5, 2)

    def test_none_input(self):
        assert parse_roc_date(None) is None

    def test_empty_string(self):
        assert parse_roc_date("") is None

    def test_exclusion_not_ordered(self):
        assert parse_roc_date("未訂") is None

    def test_exclusion_no_dispatch(self):
        assert parse_roc_date("不派工") is None

    def test_exclusion_suspended(self):
        assert parse_roc_date("派工暫緩") is None

    def test_invalid_format(self):
        assert parse_roc_date("abc") is None

    def test_invalid_date_values(self):
        assert parse_roc_date("112.13.32") is None  # month 13, day 32

    def test_numeric_input(self):
        # float from Excel cell
        assert parse_roc_date(112.714) is None  # not a valid format


class TestParseSequenceNo:
    def test_simple_integer(self):
        assert parse_sequence_no(43) == 43

    def test_string_integer(self):
        assert parse_sequence_no("43") == 43

    def test_with_note(self):
        assert parse_sequence_no("43\n暫緩") == 43

    def test_none(self):
        assert parse_sequence_no(None) is None

    def test_non_numeric(self):
        assert parse_sequence_no("暫緩") is None

    def test_float_string(self):
        # "43.0" first line is "43.0", regex ^(\d+)$ won't match
        assert parse_sequence_no("43.0") is None

    def test_float_input(self):
        # float 43.0 → str "43.0", first line "43.0" → no match
        assert parse_sequence_no(43.0) is None


class TestParseAmount:
    def test_integer(self):
        assert parse_amount(1000) == 1000.0

    def test_float(self):
        assert parse_amount(1234.56) == 1234.56

    def test_string_number(self):
        assert parse_amount("1234.56") == 1234.56

    def test_none(self):
        assert parse_amount(None) is None

    def test_invalid_string(self):
        assert parse_amount("abc") is None

    def test_zero(self):
        assert parse_amount(0) == 0.0


class TestSafeCell:
    def test_in_range(self):
        row = (10, 20, 30)
        assert safe_cell(row, 1) == 20

    def test_out_of_range(self):
        row = (10, 20)
        assert safe_cell(row, 5) is None

    def test_first_element(self):
        row = (10,)
        assert safe_cell(row, 0) == 10

    def test_empty_tuple(self):
        assert safe_cell((), 0) is None


class TestParseDocLine:
    def test_standard_format(self):
        result = parse_doc_line("112.5.26桃工用字第1120021701號")
        assert result is not None
        assert result['doc_date'] == date(2023, 5, 26)
        assert result['doc_number'] == "桃工用字第1120021701號"
        assert result['sender'] == "桃園市政府工務局"

    def test_company_doc(self):
        result = parse_doc_line("112.6.1乾坤測字第1120001號")
        assert result is not None
        assert result['doc_number'] == "乾坤測字第1120001號"
        assert result['sender'] == "乾坤測繪科技有限公司"

    def test_empty_line(self):
        assert parse_doc_line("") is None

    def test_whitespace_only(self):
        assert parse_doc_line("   ") is None

    def test_parenthesis_note(self):
        assert parse_doc_line("(備註)") is None

    def test_invalid_format(self):
        assert parse_doc_line("隨便寫的文字") is None

    def test_date_with_space(self):
        result = parse_doc_line("112.5.26 桃工用字第1120021701號")
        assert result is not None
        assert result['doc_number'] == "桃工用字第1120021701號"

    def test_invalid_date_in_doc(self):
        assert parse_doc_line("112.13.32桃工用字第001號") is None

    def test_unknown_prefix(self):
        result = parse_doc_line("112.5.26未知字第001號")
        assert result is not None
        assert result['sender'] is None
        assert result['doc_number'] == "未知字第001號"

    def test_fu_gong_prefix(self):
        result = parse_doc_line("113.1.15府工用字第1130001號")
        assert result is not None
        assert result['sender'] == "桃園市政府工務局"
