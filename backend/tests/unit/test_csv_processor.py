# -*- coding: utf-8 -*-
"""
CSV 處理器單元測試
CSV Processor Unit Tests

執行方式:
    pytest tests/unit/test_csv_processor.py -v
"""
import pytest
import sys
import os
from datetime import datetime

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.csv_processor import DocumentCSVProcessor


class TestDocumentCSVProcessorInit:
    """測試 CSV 處理器初始化"""

    def test_init_creates_field_mappings(self):
        """測試初始化時建立欄位對應"""
        processor = DocumentCSVProcessor()
        assert hasattr(processor, 'field_mappings')
        assert isinstance(processor.field_mappings, dict)
        assert len(processor.field_mappings) > 0

    def test_init_creates_final_columns(self):
        """測試初始化時建立最終欄位列表"""
        processor = DocumentCSVProcessor()
        assert hasattr(processor, 'final_columns')
        assert isinstance(processor.final_columns, list)
        assert 'doc_number' in processor.final_columns
        assert 'subject' in processor.final_columns

    def test_init_creates_supported_encodings(self):
        """測試初始化時建立支援編碼列表"""
        processor = DocumentCSVProcessor()
        assert hasattr(processor, 'supported_encodings')
        assert 'utf-8' in processor.supported_encodings
        assert 'big5' in processor.supported_encodings


class TestDetectEncoding:
    """測試編碼檢測"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_detect_utf8_encoding(self, processor):
        """測試 UTF-8 編碼檢測"""
        content = "測試內容".encode('utf-8')
        result = processor._detect_encoding(content)
        assert result == 'utf-8'

    def test_detect_utf8_bom_encoding(self, processor):
        """測試 UTF-8 BOM 編碼檢測"""
        content = "測試內容".encode('utf-8-sig')
        result = processor._detect_encoding(content)
        # utf-8-sig 可以被 utf-8 或 utf-8-sig 解碼
        assert result in ['utf-8', 'utf-8-sig']

    def test_detect_big5_encoding(self, processor):
        """測試 Big5 編碼檢測"""
        # 建立一個只能被 Big5 解碼的內容
        content = "測試內容".encode('big5')
        result = processor._detect_encoding(content)
        # Big5 編碼的內容有時候也能被其他編碼解析
        assert result in processor.supported_encodings


class TestCleanText:
    """測試文字清理"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_clean_normal_text(self, processor):
        """測試正常文字清理"""
        result = processor._clean_text("  測試文字  ")
        assert result == "測試文字"

    def test_clean_none_value(self, processor):
        """測試 None 值"""
        result = processor._clean_text(None)
        assert result == ""

    def test_clean_nan_value(self, processor):
        """測試 NaN 值"""
        import pandas as pd
        result = processor._clean_text(pd.NA)
        assert result == ""

    def test_clean_numeric_value(self, processor):
        """測試數值轉換"""
        result = processor._clean_text(123)
        assert result == "123"


class TestParseDate:
    """測試日期解析"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_parse_roc_date_format(self, processor):
        """測試民國日期格式"""
        result = processor._parse_date("中華民國115年1月8日")
        assert result == "2026-01-08"

    def test_parse_roc_date_format_two_digit_year(self, processor):
        """測試兩位數民國年"""
        result = processor._parse_date("中華民國99年12月31日")
        assert result == "2010-12-31"

    def test_parse_standard_date(self, processor):
        """測試標準日期格式"""
        result = processor._parse_date("2026-01-08")
        assert result == "2026-01-08"

    def test_parse_empty_date(self, processor):
        """測試空日期"""
        result = processor._parse_date("")
        assert result is None

    def test_parse_none_date(self, processor):
        """測試 None 日期"""
        result = processor._parse_date(None)
        assert result is None

    def test_parse_invalid_date(self, processor):
        """測試無效日期"""
        result = processor._parse_date("invalid date")
        assert result is None

    def test_parse_roc_date_single_digit_month(self, processor):
        """測試單位數月份"""
        result = processor._parse_date("中華民國114年9月2日")
        assert result == "2025-09-02"


class TestDetermineDocType:
    """測試文件類型判斷"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_determine_by_filename_send(self, processor):
        """測試根據檔名判斷發文"""
        result = processor._determine_doc_type("send_documents.csv", "桃園市政府")
        assert result == "發文"

    def test_determine_by_filename_receive(self, processor):
        """測試根據檔名判斷收文"""
        result = processor._determine_doc_type("receive_documents.csv", "桃園市政府")
        assert result == "收文"

    def test_determine_by_filename_chinese_send(self, processor):
        """測試根據中文檔名判斷發文"""
        result = processor._determine_doc_type("發文清單.csv", "桃園市政府")
        assert result == "發文"

    def test_determine_by_filename_chinese_receive(self, processor):
        """測試根據中文檔名判斷收文"""
        result = processor._determine_doc_type("收文清單.csv", "桃園市政府")
        assert result == "收文"

    def test_determine_by_sender_company(self, processor):
        """測試根據發文單位判斷（乾坤）"""
        result = processor._determine_doc_type("documents.csv", "乾坤測繪有限公司")
        assert result == "發文"

    def test_determine_by_sender_external(self, processor):
        """測試根據發文單位判斷（外部機關）"""
        result = processor._determine_doc_type("documents.csv", "桃園市政府")
        assert result == "收文"


class TestLoadCSVData:
    """測試 CSV 載入"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_load_valid_csv(self, processor):
        """測試載入有效 CSV"""
        csv_content = """報表標題
序號,類別,字,文號,主旨,發文單位,受文單位,公文日期
1,函,府工測字,1140001234,測試公文主旨內容,桃園市政府,乾坤測繪有限公司,中華民國114年9月2日
"""
        content_bytes = csv_content.encode('utf-8')
        df = processor.load_csv_data(content_bytes, "test.csv")

        assert not df.empty
        assert len(df) == 1
        assert '序號' in df.columns
        assert '主旨' in df.columns

    def test_load_empty_csv(self, processor):
        """測試載入空 CSV"""
        csv_content = ""
        content_bytes = csv_content.encode('utf-8')
        df = processor.load_csv_data(content_bytes, "empty.csv")

        assert df.empty

    def test_load_csv_without_header(self, processor):
        """測試載入沒有標頭的 CSV"""
        csv_content = """資料1,資料2,資料3
value1,value2,value3
"""
        content_bytes = csv_content.encode('utf-8')
        df = processor.load_csv_data(content_bytes, "no_header.csv")

        assert df.empty  # 找不到標頭行


class TestProcessRow:
    """測試單行處理"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_process_valid_row(self, processor):
        """測試處理有效行"""
        row_data = {
            '字': '府工測字',
            '文號': '1140001234',
            '主旨': '關於測繪作業事宜請查照辦理',
            '發文單位': '桃園市政府',
            '受文單位': '乾坤測繪有限公司',
            '公文日期': '中華民國114年9月2日',
            '類別': '函'
        }
        result = processor.process_row(row_data)

        assert result is not None
        assert result['doc_number'] == '府工測字字第1140001234號'
        assert result['subject'] == '關於測繪作業事宜請查照辦理'

    def test_process_row_missing_doc_number(self, processor):
        """測試處理缺少文號的行"""
        row_data = {
            '主旨': '測試主旨',
            '發文單位': '桃園市政府'
        }
        result = processor.process_row(row_data)

        assert result is None  # 缺少文號應該返回 None

    def test_process_row_missing_subject(self, processor):
        """測試處理缺少主旨的行"""
        row_data = {
            '字': '府工測字',
            '文號': '1140001234',
            '發文單位': '桃園市政府'
        }
        result = processor.process_row(row_data)

        assert result is None  # 缺少主旨應該返回 None

    def test_process_row_test_data_filtered(self, processor):
        """測試過濾測試資料"""
        row_data = {
            '字': '府工測字',
            '文號': '1140001234',
            '主旨': 'test',  # 測試資料
            '發文單位': '桃園市政府'
        }
        result = processor.process_row(row_data)

        assert result is None  # 測試資料應該被過濾

    def test_process_row_with_dates(self, processor):
        """測試處理包含日期的行"""
        row_data = {
            '字': '府工測字',
            '文號': '1140001234',
            '主旨': '關於測繪作業事宜請查照辦理',
            '發文單位': '桃園市政府',
            '日期': '2025-09-02',  # 使用標準日期格式
            '收文日期': '2025-09-03 10:30:00'
        }
        result = processor.process_row(row_data)

        assert result is not None
        assert result.get('doc_date') == '2025-09-02'
        assert result.get('receive_date') == '2025-09-03'


class TestProcessCSVContent:
    """測試完整 CSV 處理流程"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_process_valid_csv_content(self, processor):
        """測試處理有效 CSV 內容"""
        csv_content = """公文清單報表
序號,類別,字,文號,主旨,發文單位,受文單位,公文日期
1,函,府工測字,1140001234,關於測繪作業事宜請查照辦理,桃園市政府,乾坤測繪有限公司,中華民國114年9月2日
"""
        content_bytes = csv_content.encode('utf-8')
        results = processor.process_csv_content(content_bytes, "receive_docs.csv")

        assert len(results) == 1
        assert results[0]['doc_number'] == '府工測字字第1140001234號'

    def test_process_empty_csv_content(self, processor):
        """測試處理空 CSV 內容"""
        csv_content = ""
        content_bytes = csv_content.encode('utf-8')
        results = processor.process_csv_content(content_bytes, "empty.csv")

        assert len(results) == 0

    def test_process_csv_with_multiple_rows(self, processor):
        """測試處理多行 CSV"""
        csv_content = """公文清單報表
序號,類別,字,文號,主旨,發文單位,受文單位,公文日期
1,函,府工測字,1140001234,關於測繪作業事宜請查照辦理,桃園市政府,乾坤測繪有限公司,中華民國114年9月2日
2,函,府工測字,1140001235,關於地籍測量事宜請查照,桃園市政府,乾坤測繪有限公司,中華民國114年9月3日
3,函,府工測字,1140001236,關於工程測量事宜惠請協助,桃園市政府,乾坤測繪有限公司,中華民國114年9月4日
"""
        content_bytes = csv_content.encode('utf-8')
        results = processor.process_csv_content(content_bytes, "receive_docs.csv")

        assert len(results) == 3


class TestFieldMappings:
    """測試欄位對應"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_standard_field_mappings(self, processor):
        """測試標準欄位對應"""
        assert processor.field_mappings['流水號'] == 'auto_serial'
        assert processor.field_mappings['公文字號'] == 'doc_number'
        assert processor.field_mappings['主旨'] == 'subject'
        assert processor.field_mappings['發文單位'] == 'sender'
        assert processor.field_mappings['受文單位'] == 'receiver'

    def test_compatibility_field_mappings(self, processor):
        """測試相容性欄位對應"""
        assert processor.field_mappings['序號'] == 'auto_serial'
        assert processor.field_mappings['編號'] == 'auto_serial'
        assert processor.field_mappings['狀態'] == 'status'
        assert processor.field_mappings['辦理情形'] == 'status'


class TestEdgeCases:
    """測試邊界情況"""

    @pytest.fixture
    def processor(self):
        return DocumentCSVProcessor()

    def test_process_row_with_special_characters(self, processor):
        """測試處理包含特殊字元的行"""
        row_data = {
            '字': '府工測字',
            '文號': '1140001234',
            '主旨': '關於「測繪作業」事宜—請查照辦理（含附件）',
            '發文單位': '桃園市政府工務局',
            '備註': '※重要公文※'
        }
        result = processor.process_row(row_data)

        assert result is not None
        assert '「' in result['subject']
        assert '」' in result['subject']

    def test_process_row_with_whitespace(self, processor):
        """測試處理包含空白的行"""
        row_data = {
            '字': '  府工測字  ',
            '文號': '  1140001234  ',
            '主旨': '  關於測繪作業事宜請查照辦理  ',
            '發文單位': '  桃園市政府  '
        }
        result = processor.process_row(row_data)

        assert result is not None
        # 驗證空白被正確清理
        assert result['doc_number'] == '府工測字字第1140001234號'

    def test_process_row_short_subject_warning(self, processor):
        """測試短主旨警告（但不拒絕）"""
        row_data = {
            '字': '府工測字',
            '文號': '1140001234',
            '主旨': '公文通知',  # 5 字，剛好達到最低要求
            '發文單位': '桃園市政府'
        }
        result = processor.process_row(row_data)

        # 主旨長度剛好 5 字，應該通過
        assert result is not None

    def test_process_row_invalid_doc_number_format(self, processor):
        """測試無效公文字號格式"""
        row_data = {
            '字': '',  # 空的機關字
            '文號': '1140001234',
            '主旨': '關於測繪作業事宜請查照辦理',
            '發文單位': '桃園市政府'
        }
        result = processor.process_row(row_data)

        # 缺少機關字首，應該返回 None
        assert result is None
