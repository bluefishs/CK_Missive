# -*- coding: utf-8 -*-
"""
公文服務單元測試
Document Service Unit Tests

執行方式:
    pytest tests/unit/test_document_service.py -v
"""
import pytest
import sys
import os
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestDocumentServiceFilters:
    """測試公文服務篩選功能"""

    def test_filter_doc_type(self):
        """測試公文類型篩選"""
        from app.schemas.document import DocumentFilter

        filter_obj = DocumentFilter(doc_type="函")
        assert filter_obj.doc_type == "函"

    def test_filter_year(self):
        """測試年度篩選"""
        from app.schemas.document import DocumentFilter

        filter_obj = DocumentFilter(year=2026)
        assert filter_obj.year == 2026

    def test_filter_keyword(self):
        """測試關鍵字篩選"""
        from app.schemas.document import DocumentFilter

        filter_obj = DocumentFilter(keyword="測繪")
        assert filter_obj.keyword == "測繪"

    def test_filter_date_range(self):
        """測試日期範圍篩選"""
        from app.schemas.document import DocumentFilter

        filter_obj = DocumentFilter(
            date_from="2026-01-01",
            date_to="2026-12-31"
        )
        assert filter_obj.date_from == "2026-01-01"
        assert filter_obj.date_to == "2026-12-31"

    def test_filter_sender_receiver(self):
        """測試發受文單位篩選"""
        from app.schemas.document import DocumentFilter

        filter_obj = DocumentFilter(
            sender="桃園市政府",
            receiver="乾坤測繪"
        )
        assert filter_obj.sender == "桃園市政府"
        assert filter_obj.receiver == "乾坤測繪"

    def test_filter_contract_case(self):
        """測試承攬案件篩選"""
        from app.schemas.document import DocumentFilter

        filter_obj = DocumentFilter(contract_case="測繪專案")
        assert filter_obj.contract_case == "測繪專案"

    def test_filter_delivery_method(self):
        """測試發文形式篩選"""
        from app.schemas.document import DocumentFilter

        filter_obj = DocumentFilter(delivery_method="電子交換")
        assert filter_obj.delivery_method == "電子交換"

    def test_filter_category(self):
        """測試收發文類別篩選"""
        from app.schemas.document import DocumentFilter

        filter_obj = DocumentFilter(category="收文")
        assert filter_obj.category == "收文"


class TestDocumentListQuery:
    """測試公文列表查詢參數"""

    def test_default_pagination(self):
        """測試預設分頁參數"""
        from app.schemas.document import DocumentListQuery

        query = DocumentListQuery()
        assert query.page == 1
        assert query.limit == 20

    def test_custom_pagination(self):
        """測試自訂分頁參數"""
        from app.schemas.document import DocumentListQuery

        query = DocumentListQuery(page=3, limit=50)
        assert query.page == 3
        assert query.limit == 50

    def test_query_with_filters(self):
        """測試帶有篩選條件的查詢"""
        from app.schemas.document import DocumentListQuery

        query = DocumentListQuery(
            keyword="測試",
            doc_type="函",
            year=2026,
            page=2,
            limit=10
        )
        assert query.keyword == "測試"
        assert query.doc_type == "函"
        assert query.year == 2026


class TestDocumentResponse:
    """測試公文回應結構"""

    def test_document_response_validation(self):
        """測試公文回應驗證"""
        from app.schemas.document import DocumentResponse

        # 建立一個模擬的文檔資料
        doc_data = {
            "id": 1,
            "auto_serial": "R0001",
            "doc_number": "府工測字字第1140001234號",
            "doc_type": "函",
            "subject": "關於測繪作業事宜",
            "sender": "桃園市政府",
            "receiver": "乾坤測繪有限公司",
            "doc_date": date(2026, 1, 8),
            "status": "待處理",
            "category": "收文",
            "created_at": datetime(2026, 1, 8, 10, 0, 0),
            "updated_at": datetime(2026, 1, 8, 10, 0, 0)
        }

        response = DocumentResponse.model_validate(doc_data)
        assert response.id == 1
        assert response.doc_number == "府工測字字第1140001234號"

    def test_document_response_with_relations(self):
        """測試帶有關聯資料的公文回應"""
        from app.schemas.document import DocumentResponse

        doc_data = {
            "id": 2,
            "auto_serial": "S0001",
            "doc_number": "乾坤測字第1140000001號",
            "doc_type": "函",
            "subject": "函覆測繪作業事宜",
            "sender": "乾坤測繪有限公司",
            "receiver": "桃園市政府",
            "doc_date": date(2026, 1, 9),
            "status": "已發送",
            "category": "發文",
            "contract_project_id": 1,
            "contract_project_name": "桃園測繪專案",
            "attachment_count": 3,
            "created_at": datetime(2026, 1, 9, 10, 0, 0),
            "updated_at": datetime(2026, 1, 9, 10, 0, 0)
        }

        response = DocumentResponse.model_validate(doc_data)
        assert response.contract_project_name == "桃園測繪專案"
        assert response.attachment_count == 3


class TestDocumentImportResult:
    """測試公文匯入結果"""

    def test_import_result_success(self):
        """測試成功匯入結果"""
        from app.schemas.document import DocumentImportResult

        result = DocumentImportResult(
            total_rows=100,
            success_count=95,
            error_count=3,
            skipped_count=2,
            errors=["行10: 缺少公文字號", "行25: 日期格式錯誤", "行50: 主旨為空"],
            processing_time=1.5
        )

        assert result.total_rows == 100
        assert result.success_count == 95
        assert result.error_count == 3
        assert result.skipped_count == 2
        assert len(result.errors) == 3
        assert result.processing_time == 1.5

    def test_import_result_all_success(self):
        """測試全部成功匯入結果"""
        from app.schemas.document import DocumentImportResult

        result = DocumentImportResult(
            total_rows=50,
            success_count=50,
            error_count=0,
            skipped_count=0,
            errors=[],
            processing_time=0.8
        )

        assert result.success_count == result.total_rows
        assert result.error_count == 0
        assert len(result.errors) == 0


class TestPaginationMeta:
    """測試分頁元資料"""

    def test_pagination_create(self):
        """測試分頁元資料建立"""
        from app.schemas.common import PaginationMeta

        pagination = PaginationMeta.create(total=100, page=1, limit=20)

        assert pagination.total == 100
        assert pagination.page == 1
        assert pagination.limit == 20
        assert pagination.total_pages == 5
        assert pagination.has_next is True
        assert pagination.has_prev is False

    def test_pagination_last_page(self):
        """測試最後一頁"""
        from app.schemas.common import PaginationMeta

        pagination = PaginationMeta.create(total=100, page=5, limit=20)

        assert pagination.has_next is False
        assert pagination.has_prev is True

    def test_pagination_single_page(self):
        """測試單頁結果"""
        from app.schemas.common import PaginationMeta

        pagination = PaginationMeta.create(total=10, page=1, limit=20)

        assert pagination.total_pages == 1
        assert pagination.has_next is False
        assert pagination.has_prev is False

    def test_pagination_empty_result(self):
        """測試空結果"""
        from app.schemas.common import PaginationMeta

        pagination = PaginationMeta.create(total=0, page=1, limit=20)

        assert pagination.total == 0
        assert pagination.total_pages == 0


class TestDocumentValidation:
    """測試公文資料驗證"""

    def test_valid_doc_type(self):
        """測試有效公文類型"""
        from app.services.base.validators import DocumentValidators

        assert DocumentValidators.validate_doc_type("函") == "函"
        assert DocumentValidators.validate_doc_type("開會通知單") == "開會通知單"
        assert DocumentValidators.validate_doc_type("書函") == "書函"

    def test_invalid_doc_type_auto_fix(self):
        """測試無效公文類型自動修正"""
        from app.services.base.validators import DocumentValidators

        result = DocumentValidators.validate_doc_type("無效類型", auto_fix=True)
        assert result == "函"  # 預設修正為 "函"

    def test_valid_category(self):
        """測試有效類別"""
        from app.services.base.validators import DocumentValidators

        assert DocumentValidators.validate_category("收文") == "收文"
        assert DocumentValidators.validate_category("發文") == "發文"

    def test_invalid_category_raises(self):
        """測試無效類別拋出錯誤"""
        from app.services.base.validators import DocumentValidators

        with pytest.raises(ValueError):
            DocumentValidators.validate_category("無效類別")


class TestDateParsing:
    """測試日期解析"""

    def test_parse_roc_date(self):
        """測試民國日期解析"""
        from app.services.base.validators import DateParsers

        result = DateParsers.parse_date("民國115年1月8日")
        assert result == date(2026, 1, 8)

    def test_parse_full_roc_date(self):
        """測試完整民國日期解析"""
        from app.services.base.validators import DateParsers

        result = DateParsers.parse_date("中華民國115年1月8日")
        assert result == date(2026, 1, 8)

    def test_parse_standard_date(self):
        """測試標準日期解析"""
        from app.services.base.validators import DateParsers

        result = DateParsers.parse_date("2026-01-08")
        assert result == date(2026, 1, 8)

    def test_parse_date_with_time(self):
        """測試含時間的日期解析"""
        from app.services.base.validators import DateParsers

        result = DateParsers.parse_date("2026-01-08 10:30:00")
        assert result == date(2026, 1, 8)


class TestStringCleaners:
    """測試字串清理"""

    def test_clean_string(self):
        """測試字串清理"""
        from app.services.base.validators import StringCleaners

        assert StringCleaners.clean_string("  測試  ") == "測試"
        assert StringCleaners.clean_string("None") is None
        assert StringCleaners.clean_string("null") is None

    def test_clean_agency_name(self):
        """測試機關名稱清理"""
        from app.services.base.validators import StringCleaners

        # 帶代碼的機關名稱
        result = StringCleaners.clean_agency_name("桃園市政府(10002)")
        assert result == "桃園市政府"

        # 純名稱
        result = StringCleaners.clean_agency_name("桃園市政府工務局")
        assert result == "桃園市政府工務局"


class TestDocumentSearchRequest:
    """測試公文搜尋請求"""

    def test_search_request_basic(self):
        """測試基本搜尋請求"""
        from app.schemas.document import DocumentSearchRequest

        request = DocumentSearchRequest(
            keyword="測繪",
            page=1,
            limit=20
        )
        assert request.keyword == "測繪"

    def test_search_request_with_filters(self):
        """測試帶有篩選的搜尋請求"""
        from app.schemas.document import DocumentSearchRequest
        from datetime import date

        request = DocumentSearchRequest(
            doc_types=["收文"],  # 使用 doc_types (複數)
            senders=["桃園市政府"],
            doc_date_from=date(2026, 1, 1),
            doc_date_to=date(2026, 12, 31)
        )
        assert "收文" in request.doc_types
        assert "桃園市政府" in request.senders
        assert request.doc_date_from == date(2026, 1, 1)


class TestDocumentListResponse:
    """測試公文列表回應"""

    def test_list_response_structure(self):
        """測試列表回應結構"""
        from app.schemas.document import DocumentListResponse, DocumentResponse
        from app.schemas.common import PaginationMeta

        items = [
            DocumentResponse(
                id=1,
                auto_serial="R0001",
                doc_number="府工測字字第1140001234號",
                doc_type="函",
                subject="測試主旨",
                sender="桃園市政府",
                receiver="乾坤測繪",
                doc_date=date(2026, 1, 8),
                status="待處理",
                category="收文",
                created_at=datetime(2026, 1, 8, 10, 0, 0),
                updated_at=datetime(2026, 1, 8, 10, 0, 0)
            )
        ]

        pagination = PaginationMeta.create(total=1, page=1, limit=20)

        response = DocumentListResponse(
            items=items,
            pagination=pagination
        )

        assert len(response.items) == 1
        assert response.pagination.total == 1
        assert response.success is True
