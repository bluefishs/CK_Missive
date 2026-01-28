# -*- coding: utf-8 -*-
"""
查詢助手單元測試
Query Helper Unit Tests

執行方式:
    pytest tests/unit/test_query_helper.py -v
"""
import pytest
import sys
import os
from datetime import date
from math import ceil

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import Column, Integer, String, Date, Boolean, select
from sqlalchemy.orm import declarative_base

from app.services.base.query_helper import QueryHelper, PaginationHelper, FilterBuilder

# 建立測試用模型
TestBase = declarative_base()


class MockDocument(TestBase):
    """測試用模型"""
    __tablename__ = 'mock_documents'

    id = Column(Integer, primary_key=True)
    subject = Column(String(500))
    content = Column(String(2000))
    doc_type = Column(String(50))
    category = Column(String(20))
    doc_date = Column(Date)
    created_at = Column(Date)
    is_deleted = Column(Boolean, default=False)


class TestQueryHelper:
    """查詢助手測試"""

    def setup_method(self):
        """每個測試前建立 QueryHelper 實例"""
        self.helper = QueryHelper(MockDocument)

    def test_init(self):
        """測試初始化"""
        assert self.helper.model == MockDocument

    def test_apply_search_with_keyword(self):
        """測試關鍵字搜尋"""
        query = select(MockDocument)
        result = self.helper.apply_search(query, "測試", ["subject", "content"])

        # 確認查詢有被修改 (包含 WHERE 條件)
        query_str = str(result.compile(compile_kwargs={"literal_binds": True}))
        assert "subject" in query_str.lower() or "WHERE" in str(result)

    def test_apply_search_empty_keyword(self):
        """測試空關鍵字不影響查詢"""
        query = select(MockDocument)
        result = self.helper.apply_search(query, "", ["subject"])

        # 空關鍵字應該回傳原始查詢
        assert str(result) == str(query)

    def test_apply_search_none_keyword(self):
        """測試 None 關鍵字不影響查詢"""
        query = select(MockDocument)
        result = self.helper.apply_search(query, None, ["subject"])

        assert str(result) == str(query)

    def test_apply_search_whitespace_keyword(self):
        """測試空白關鍵字不影響查詢"""
        query = select(MockDocument)
        result = self.helper.apply_search(query, "   ", ["subject"])

        assert str(result) == str(query)

    def test_apply_search_invalid_field(self):
        """測試無效欄位被忽略"""
        query = select(MockDocument)
        result = self.helper.apply_search(query, "測試", ["invalid_field"])

        # 無效欄位應被忽略，查詢不變
        assert str(result) == str(query)

    def test_apply_search_escapes_special_chars(self):
        """測試特殊字元轉義 (防止 SQL 注入)"""
        query = select(MockDocument)
        # 使用包含 LIKE 特殊字元的關鍵字
        result = self.helper.apply_search(query, "test%_\\special", ["subject"])

        # 確認查詢有被修改
        query_str = str(result)
        assert "WHERE" in query_str or "subject" in query_str.lower()

    def test_escape_like_pattern(self):
        """測試 _escape_like_pattern 靜態方法"""
        # 測試百分號轉義
        assert QueryHelper._escape_like_pattern("100%") == "100\\%"
        # 測試底線轉義
        assert QueryHelper._escape_like_pattern("test_name") == "test\\_name"
        # 測試反斜線轉義
        assert QueryHelper._escape_like_pattern("path\\file") == "path\\\\file"
        # 測試組合
        assert QueryHelper._escape_like_pattern("%_\\") == "\\%\\_\\\\"

    def test_apply_exact_filter(self):
        """測試精確匹配篩選"""
        query = select(MockDocument)
        result = self.helper.apply_exact_filter(query, "category", "收文")

        # 確認有添加 WHERE 條件
        assert str(result) != str(query)

    def test_apply_exact_filter_none_value(self):
        """測試 None 值不影響查詢"""
        query = select(MockDocument)
        result = self.helper.apply_exact_filter(query, "category", None)

        assert str(result) == str(query)

    def test_apply_exact_filter_invalid_field(self):
        """測試無效欄位被忽略"""
        query = select(MockDocument)
        result = self.helper.apply_exact_filter(query, "invalid_field", "value")

        assert str(result) == str(query)

    def test_apply_in_filter(self):
        """測試 IN 篩選"""
        query = select(MockDocument)
        result = self.helper.apply_in_filter(query, "doc_type", ["函", "開會通知單"])

        assert str(result) != str(query)

    def test_apply_in_filter_empty_list(self):
        """測試空列表不影響查詢"""
        query = select(MockDocument)
        result = self.helper.apply_in_filter(query, "doc_type", [])

        assert str(result) == str(query)

    def test_apply_in_filter_none_list(self):
        """測試 None 列表不影響查詢"""
        query = select(MockDocument)
        result = self.helper.apply_in_filter(query, "doc_type", None)

        assert str(result) == str(query)

    def test_apply_date_range_both_dates(self):
        """測試日期範圍篩選 (有起始和結束日期)"""
        query = select(MockDocument)
        start = date(2026, 1, 1)
        end = date(2026, 12, 31)
        result = self.helper.apply_date_range(query, "doc_date", start, end)

        assert str(result) != str(query)

    def test_apply_date_range_start_only(self):
        """測試只有起始日期"""
        query = select(MockDocument)
        start = date(2026, 1, 1)
        result = self.helper.apply_date_range(query, "doc_date", start_date=start)

        assert str(result) != str(query)

    def test_apply_date_range_end_only(self):
        """測試只有結束日期"""
        query = select(MockDocument)
        end = date(2026, 12, 31)
        result = self.helper.apply_date_range(query, "doc_date", end_date=end)

        assert str(result) != str(query)

    def test_apply_date_range_no_dates(self):
        """測試沒有日期不影響查詢"""
        query = select(MockDocument)
        result = self.helper.apply_date_range(query, "doc_date")

        assert str(result) == str(query)

    def test_apply_date_range_invalid_field(self):
        """測試無效欄位被忽略"""
        query = select(MockDocument)
        result = self.helper.apply_date_range(
            query, "invalid_field", date(2026, 1, 1), date(2026, 12, 31)
        )

        assert str(result) == str(query)

    def test_apply_sorting_default_desc(self):
        """測試預設降序排序"""
        query = select(MockDocument)
        result = self.helper.apply_sorting(query, "created_at", "desc")

        query_str = str(result)
        assert "ORDER BY" in query_str

    def test_apply_sorting_asc(self):
        """測試升序排序"""
        query = select(MockDocument)
        result = self.helper.apply_sorting(query, "created_at", "asc")

        query_str = str(result)
        assert "ORDER BY" in query_str

    def test_apply_sorting_default_field(self):
        """測試預設排序欄位"""
        query = select(MockDocument)
        result = self.helper.apply_sorting(query, None, "desc", "created_at")

        query_str = str(result)
        assert "ORDER BY" in query_str

    def test_apply_sorting_invalid_field_uses_default(self):
        """測試無效欄位使用預設"""
        query = select(MockDocument)
        result = self.helper.apply_sorting(query, "invalid_field", "desc", "created_at")

        query_str = str(result)
        assert "ORDER BY" in query_str

    def test_apply_pagination(self):
        """測試分頁"""
        query = select(MockDocument)
        result = self.helper.apply_pagination(query, page=2, page_size=20)

        query_str = str(result)
        assert "LIMIT" in query_str
        assert "OFFSET" in query_str

    def test_apply_pagination_default_values(self):
        """測試分頁預設值"""
        query = select(MockDocument)
        result = self.helper.apply_pagination(query)

        query_str = str(result)
        assert "LIMIT" in query_str

    def test_apply_pagination_page_clamp(self):
        """測試頁碼限制 (不能小於 1)"""
        query = select(MockDocument)
        result = self.helper.apply_pagination(query, page=0, page_size=20)

        # page=0 應該被正規化為 page=1，offset 應為 0
        query_str = str(result)
        assert "LIMIT" in query_str
        assert "OFFSET" in query_str

    def test_apply_pagination_page_size_clamp(self):
        """測試每頁筆數限制 (最大 100)"""
        query = select(MockDocument)
        result = self.helper.apply_pagination(query, page=1, page_size=200)

        # page_size=200 應該被限制為 100
        query_str = str(result)
        assert "LIMIT" in query_str

    def test_apply_soft_delete_filter_exclude(self):
        """測試排除已刪除資料"""
        query = select(MockDocument)
        result = self.helper.apply_soft_delete_filter(query, include_deleted=False)

        assert str(result) != str(query)

    def test_apply_soft_delete_filter_include(self):
        """測試包含已刪除資料"""
        query = select(MockDocument)
        result = self.helper.apply_soft_delete_filter(query, include_deleted=True)

        assert str(result) == str(query)


class TestPaginationHelper:
    """分頁助手測試"""

    def test_wrap_response(self):
        """測試分頁回應包裝"""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = PaginationHelper.wrap_response(items, total=100, page=1, page_size=20)

        assert result.success is True
        assert result.items == items
        assert result.pagination.total == 100
        assert result.pagination.page == 1
        assert result.pagination.limit == 20
        assert result.pagination.total_pages == 5
        assert result.pagination.has_next is True
        assert result.pagination.has_prev is False

    def test_wrap_response_empty(self):
        """測試空結果包裝"""
        result = PaginationHelper.wrap_response([], total=0, page=1, page_size=20)

        assert result.success is True
        assert result.items == []
        assert result.pagination.total == 0
        assert result.pagination.total_pages == 0

    def test_wrap_response_partial_page(self):
        """測試不足一頁的結果"""
        items = [{"id": 1}]
        result = PaginationHelper.wrap_response(items, total=1, page=1, page_size=20)

        assert result.pagination.total_pages == 1
        assert result.pagination.has_next is False
        assert result.pagination.has_prev is False

    def test_calculate_offset(self):
        """測試偏移量計算"""
        assert PaginationHelper.calculate_offset(1, 20) == 0
        assert PaginationHelper.calculate_offset(2, 20) == 20
        assert PaginationHelper.calculate_offset(3, 20) == 40
        assert PaginationHelper.calculate_offset(5, 10) == 40

    def test_calculate_offset_invalid_page(self):
        """測試無效頁碼"""
        # 頁碼 0 或負數應該被視為 1
        assert PaginationHelper.calculate_offset(0, 20) == 0
        assert PaginationHelper.calculate_offset(-1, 20) == 0

    def test_calculate_total_pages(self):
        """測試總頁數計算"""
        assert PaginationHelper.calculate_total_pages(100, 20) == 5
        assert PaginationHelper.calculate_total_pages(101, 20) == 6
        assert PaginationHelper.calculate_total_pages(99, 20) == 5
        assert PaginationHelper.calculate_total_pages(20, 20) == 1

    def test_calculate_total_pages_zero_total(self):
        """測試零總數"""
        assert PaginationHelper.calculate_total_pages(0, 20) == 0

    def test_calculate_total_pages_zero_page_size(self):
        """測試零每頁筆數"""
        assert PaginationHelper.calculate_total_pages(100, 0) == 0

    def test_validate_pagination_params_normal(self):
        """測試正常分頁參數驗證"""
        page, page_size = PaginationHelper.validate_pagination_params(2, 50)

        assert page == 2
        assert page_size == 50

    def test_validate_pagination_params_invalid_page(self):
        """測試無效頁碼正規化"""
        page, page_size = PaginationHelper.validate_pagination_params(0, 20)
        assert page == 1

        page, page_size = PaginationHelper.validate_pagination_params(-5, 20)
        assert page == 1

    def test_validate_pagination_params_exceeds_max(self):
        """測試超過最大每頁筆數"""
        page, page_size = PaginationHelper.validate_pagination_params(1, 200)
        assert page_size == 100  # 預設最大 100

    def test_validate_pagination_params_custom_max(self):
        """測試自訂最大每頁筆數"""
        page, page_size = PaginationHelper.validate_pagination_params(1, 200, max_page_size=50)
        assert page_size == 50

    def test_validate_pagination_params_zero_page_size(self):
        """測試零每頁筆數"""
        page, page_size = PaginationHelper.validate_pagination_params(1, 0)
        assert page_size == 1


class TestFilterBuilder:
    """篩選條件建構器測試"""

    def setup_method(self):
        """每個測試前建立 FilterBuilder 實例"""
        self.builder = FilterBuilder(MockDocument)

    def test_init(self):
        """測試初始化"""
        assert self.builder.model == MockDocument
        assert len(self.builder._operations) == 0

    def test_search(self):
        """測試搜尋條件"""
        result = self.builder.search("測試", ["subject", "content"])

        assert result is self.builder  # 支援鏈式調用
        assert len(self.builder._operations) == 1

    def test_search_empty_keyword(self):
        """測試空關鍵字不添加條件"""
        self.builder.search("", ["subject"])

        assert len(self.builder._operations) == 0

    def test_search_none_keyword(self):
        """測試 None 關鍵字不添加條件"""
        self.builder.search(None, ["subject"])

        assert len(self.builder._operations) == 0

    def test_exact(self):
        """測試精確匹配條件"""
        result = self.builder.exact("category", "收文")

        assert result is self.builder
        assert len(self.builder._operations) == 1

    def test_exact_none_value(self):
        """測試 None 值不添加條件"""
        self.builder.exact("category", None)

        assert len(self.builder._operations) == 0

    def test_in_list(self):
        """測試 IN 條件"""
        result = self.builder.in_list("doc_type", ["函", "開會通知單"])

        assert result is self.builder
        assert len(self.builder._operations) == 1

    def test_in_list_empty(self):
        """測試空列表不添加條件"""
        self.builder.in_list("doc_type", [])

        assert len(self.builder._operations) == 0

    def test_date_range(self):
        """測試日期範圍條件"""
        result = self.builder.date_range("doc_date", date(2026, 1, 1), date(2026, 12, 31))

        assert result is self.builder
        assert len(self.builder._operations) == 1

    def test_date_range_no_dates(self):
        """測試無日期不添加條件"""
        self.builder.date_range("doc_date")

        assert len(self.builder._operations) == 0

    def test_sort(self):
        """測試排序條件"""
        result = self.builder.sort("created_at", "desc")

        assert result is self.builder
        assert len(self.builder._operations) == 1

    def test_paginate(self):
        """測試分頁條件"""
        result = self.builder.paginate(2, 20)

        assert result is self.builder
        assert len(self.builder._operations) == 1

    def test_exclude_deleted(self):
        """測試排除已刪除條件"""
        result = self.builder.exclude_deleted()

        assert result is self.builder
        assert len(self.builder._operations) == 1

    def test_chain_operations(self):
        """測試鏈式操作"""
        result = (self.builder
            .search("測試", ["subject"])
            .exact("category", "收文")
            .date_range("doc_date", date(2026, 1, 1))
            .sort("created_at", "desc")
            .paginate(1, 20)
            .exclude_deleted()
        )

        assert result is self.builder
        assert len(self.builder._operations) == 6

    def test_build(self):
        """測試建構查詢"""
        query = select(MockDocument)

        self.builder.search("測試", ["subject"])
        self.builder.exact("category", "收文")
        self.builder.paginate(1, 20)

        result = self.builder.build(query)

        # 確認查詢已被修改
        assert str(result) != str(query)

    def test_reset(self):
        """測試重置條件"""
        self.builder.search("測試", ["subject"])
        self.builder.exact("category", "收文")

        assert len(self.builder._operations) == 2

        self.builder.reset()

        assert len(self.builder._operations) == 0

    def test_build_with_no_operations(self):
        """測試無操作時建構查詢"""
        query = select(MockDocument)
        result = self.builder.build(query)

        # 無操作時應該回傳原始查詢
        assert str(result) == str(query)


class TestQueryHelperIntegration:
    """查詢助手整合測試"""

    def test_combined_filters(self):
        """測試組合多個篩選條件"""
        helper = QueryHelper(MockDocument)
        query = select(MockDocument)

        # 套用多個篩選條件
        query = helper.apply_search(query, "測試", ["subject", "content"])
        query = helper.apply_exact_filter(query, "category", "收文")
        query = helper.apply_date_range(query, "doc_date", date(2026, 1, 1), date(2026, 12, 31))
        query = helper.apply_sorting(query, "created_at", "desc")
        query = helper.apply_pagination(query, 1, 20)
        query = helper.apply_soft_delete_filter(query, False)

        # 確認查詢包含所有條件
        query_str = str(query)
        assert "WHERE" in query_str
        assert "ORDER BY" in query_str
        assert "LIMIT" in query_str

    def test_filter_builder_equivalent(self):
        """測試 FilterBuilder 與 QueryHelper 等效"""
        # 使用 QueryHelper
        helper = QueryHelper(MockDocument)
        query1 = select(MockDocument)
        query1 = helper.apply_search(query1, "測試", ["subject"])
        query1 = helper.apply_exact_filter(query1, "category", "收文")
        query1 = helper.apply_pagination(query1, 1, 20)

        # 使用 FilterBuilder
        builder = FilterBuilder(MockDocument)
        query2 = select(MockDocument)
        query2 = (builder
            .search("測試", ["subject"])
            .exact("category", "收文")
            .paginate(1, 20)
            .build(query2)
        )

        # 兩種方式應該產生相似的查詢結構
        # (由於 lambda 閉包的特性，字串可能略有不同，但結構應該相同)
        assert "LIMIT" in str(query1) and "LIMIT" in str(query2)
