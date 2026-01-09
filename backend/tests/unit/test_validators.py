# -*- coding: utf-8 -*-
"""
驗證器單元測試
Validator Unit Tests

執行方式:
    pytest tests/unit/test_validators.py -v
"""
import pytest
import sys
import os
from datetime import date

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.base.validators import (
    DocumentValidators,
    StringCleaners,
    DateParsers
)


class TestDocumentValidators:
    """公文驗證器測試"""

    def test_validate_doc_type_valid_incoming(self):
        """測試有效收文類型"""
        assert DocumentValidators.validate_doc_type("函") == "函"
        assert DocumentValidators.validate_doc_type("開會通知單") == "開會通知單"
        assert DocumentValidators.validate_doc_type("會勘通知單") == "會勘通知單"

    def test_validate_doc_type_valid_outgoing(self):
        """測試有效發文類型"""
        assert DocumentValidators.validate_doc_type("書函") == "書函"
        assert DocumentValidators.validate_doc_type("公告") == "公告"

    def test_validate_doc_type_invalid_auto_fix(self):
        """測試無效公文類型自動修正"""
        # 無效類型應該回傳預設值 '函'
        result = DocumentValidators.validate_doc_type("無效類型")
        assert result == "函"

    def test_validate_doc_type_empty(self):
        """測試空值"""
        result = DocumentValidators.validate_doc_type("")
        assert result == "函"

    def test_validate_doc_type_none(self):
        """測試 None 值"""
        result = DocumentValidators.validate_doc_type(None)
        assert result == "函"

    def test_validate_doc_type_no_auto_fix(self):
        """測試無自動修正時拋出錯誤"""
        with pytest.raises(ValueError):
            DocumentValidators.validate_doc_type("無效類型", auto_fix=False)

    def test_validate_category_valid(self):
        """測試有效類別"""
        assert DocumentValidators.validate_category("收文") == "收文"
        assert DocumentValidators.validate_category("發文") == "發文"

    def test_validate_category_invalid(self):
        """測試無效類別拋出錯誤"""
        with pytest.raises(ValueError):
            DocumentValidators.validate_category("無效類別")

    def test_validate_category_empty(self):
        """測試空類別拋出錯誤"""
        with pytest.raises(ValueError):
            DocumentValidators.validate_category("")

    def test_validate_status_valid(self):
        """測試有效狀態"""
        assert DocumentValidators.validate_status("active") == "active"
        assert DocumentValidators.validate_status("待處理") == "待處理"
        assert DocumentValidators.validate_status("已完成") == "已完成"

    def test_validate_status_invalid(self):
        """測試無效狀態回傳預設值"""
        assert DocumentValidators.validate_status("無效狀態") == "active"

    def test_validate_status_empty(self):
        """測試空狀態回傳預設值"""
        assert DocumentValidators.validate_status("") == "active"


class TestStringCleaners:
    """字串清理器測試"""

    def test_clean_string_normal(self):
        """測試正常字串"""
        assert StringCleaners.clean_string("測試") == "測試"
        assert StringCleaners.clean_string("  測試  ") == "測試"

    def test_clean_string_none_literal(self):
        """測試 'None' 字串"""
        assert StringCleaners.clean_string("None") is None
        assert StringCleaners.clean_string("none") is None
        assert StringCleaners.clean_string("NONE") is None

    def test_clean_string_null_literal(self):
        """測試 'null' 字串"""
        assert StringCleaners.clean_string("null") is None
        assert StringCleaners.clean_string("NULL") is None

    def test_clean_string_undefined(self):
        """測試 'undefined' 字串"""
        assert StringCleaners.clean_string("undefined") is None

    def test_clean_string_actual_none(self):
        """測試實際 None 值"""
        assert StringCleaners.clean_string(None) is None

    def test_clean_string_empty(self):
        """測試空字串"""
        assert StringCleaners.clean_string("") is None

    def test_clean_string_whitespace(self):
        """測試純空白字串"""
        # 空白字串 strip 後為空，應回傳 None
        result = StringCleaners.clean_string("   ")
        assert result is None

    def test_clean_agency_name_normal(self):
        """測試正常機關名稱"""
        assert StringCleaners.clean_agency_name("桃園市政府") == "桃園市政府"

    def test_clean_agency_name_with_code(self):
        """測試帶代碼的機關名稱"""
        result = StringCleaners.clean_agency_name("桃園市政府(10002)")
        assert result == "桃園市政府"

    def test_clean_agency_name_empty(self):
        """測試空機關名稱"""
        assert StringCleaners.clean_agency_name("") is None
        assert StringCleaners.clean_agency_name(None) is None


class TestDateParsers:
    """日期解析器測試"""

    def test_parse_date_standard_format(self):
        """測試標準日期格式 YYYY-MM-DD"""
        result = DateParsers.parse_date("2026-01-08")
        assert result == date(2026, 1, 8)

    def test_parse_date_slash_format(self):
        """測試斜線格式 YYYY/MM/DD"""
        result = DateParsers.parse_date("2026/01/08")
        assert result == date(2026, 1, 8)

    def test_parse_date_dot_format(self):
        """測試點格式 YYYY.MM.DD"""
        result = DateParsers.parse_date("2026.01.08")
        assert result == date(2026, 1, 8)

    def test_parse_date_with_time(self):
        """測試含時間的日期格式"""
        result = DateParsers.parse_date("2026-01-08 10:30:00")
        assert result == date(2026, 1, 8)

    def test_parse_date_roc_format(self):
        """測試民國日期格式"""
        result = DateParsers.parse_date("民國115年1月8日")
        assert result == date(2026, 1, 8)

    def test_parse_date_roc_full_format(self):
        """測試完整民國日期格式"""
        result = DateParsers.parse_date("中華民國115年1月8日")
        assert result == date(2026, 1, 8)

    def test_parse_date_invalid(self):
        """測試無效日期"""
        result = DateParsers.parse_date("invalid")
        assert result is None

    def test_parse_date_empty(self):
        """測試空值"""
        assert DateParsers.parse_date("") is None
        assert DateParsers.parse_date(None) is None

    def test_parse_date_none_string(self):
        """測試 'none' 字串"""
        assert DateParsers.parse_date("none") is None
        assert DateParsers.parse_date("null") is None

    def test_parse_date_object(self):
        """測試已經是 date 物件"""
        d = date(2026, 1, 8)
        result = DateParsers.parse_date(d)
        assert result == d

    def test_parse_date_datetime_object(self):
        """測試 datetime 物件"""
        from datetime import datetime
        dt = datetime(2026, 1, 8, 10, 30, 0)
        result = DateParsers.parse_date(dt)
        assert result == date(2026, 1, 8)
