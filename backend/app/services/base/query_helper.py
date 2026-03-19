# -*- coding: utf-8 -*-
"""
統一查詢助手模組

提供統一的篩選、排序、搜尋邏輯，減少各服務中的重複代碼。

模組包含以下類別:
- QueryHelper: 基本查詢篩選、排序、分頁操作
- PaginationHelper: 分頁回應包裝和計算工具
- FilterBuilder: 流暢 API 建構器（鏈式調用）
- StatisticsHelper: 統計查詢功能（計數、分組、趨勢）
- DeleteCheckHelper: 刪除前關聯檢查

安全特性:
- LIKE 查詢自動轉義特殊字元，防止 SQL 注入
- 分頁參數自動驗證，防止過大查詢

版本: 1.1.0
更新: 2026-01-26
"""
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Generic
from datetime import date, datetime
from math import ceil

from sqlalchemy import Select, or_, and_, asc, desc, func, select
from sqlalchemy.orm import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import PaginatedResponse, PaginationMeta

# 泛型類型
T = TypeVar('T')
ModelType = TypeVar('ModelType')


class QueryHelper(Generic[ModelType]):
    """
    統一查詢助手

    提供通用的查詢篩選、排序、分頁功能。

    Usage:
        helper = QueryHelper(Document)
        query = helper.apply_search(query, 'keyword', ['subject', 'content'])
        query = helper.apply_date_range(query, 'doc_date', start, end)
        query = helper.apply_sorting(query, 'created_at', 'desc')
    """

    def __init__(self, model: Type[ModelType]):
        """
        初始化查詢助手

        Args:
            model: SQLAlchemy 模型類
        """
        self.model = model

    @staticmethod
    def _escape_like_pattern(keyword: str) -> str:
        """
        轉義 LIKE 模式中的特殊字元

        防止 SQL 注入和意外的萬用字元匹配。

        Args:
            keyword: 原始搜尋關鍵字

        Returns:
            轉義後的關鍵字
        """
        # 轉義 LIKE 特殊字元: %, _, \
        keyword = keyword.replace('\\', '\\\\')
        keyword = keyword.replace('%', '\\%')
        keyword = keyword.replace('_', '\\_')
        return keyword

    def apply_search(
        self,
        query: Select,
        keyword: Optional[str],
        search_fields: List[str],
        use_ilike: bool = True
    ) -> Select:
        """
        應用關鍵字搜尋

        在多個欄位中搜尋關鍵字（OR 邏輯）。

        Args:
            query: SQLAlchemy 查詢物件
            keyword: 搜尋關鍵字
            search_fields: 要搜尋的欄位名稱列表
            use_ilike: 是否使用不分大小寫的 LIKE

        Returns:
            套用篩選後的查詢物件
        """
        if not keyword or not keyword.strip():
            return query

        keyword = keyword.strip()
        # 轉義 LIKE 特殊字元以防止 SQL 注入
        escaped_keyword = self._escape_like_pattern(keyword)
        conditions = []

        for field_name in search_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                if use_ilike:
                    conditions.append(field.ilike(f'%{escaped_keyword}%', escape='\\'))
                else:
                    conditions.append(field.like(f'%{escaped_keyword}%', escape='\\'))

        if conditions:
            query = query.where(or_(*conditions))

        return query

    def apply_exact_filter(
        self,
        query: Select,
        field_name: str,
        value: Any
    ) -> Select:
        """
        應用精確匹配篩選

        Args:
            query: SQLAlchemy 查詢物件
            field_name: 欄位名稱
            value: 篩選值

        Returns:
            套用篩選後的查詢物件
        """
        if value is None:
            return query

        if hasattr(self.model, field_name):
            field = getattr(self.model, field_name)
            query = query.where(field == value)

        return query

    def apply_in_filter(
        self,
        query: Select,
        field_name: str,
        values: Optional[List[Any]]
    ) -> Select:
        """
        應用 IN 篩選

        Args:
            query: SQLAlchemy 查詢物件
            field_name: 欄位名稱
            values: 篩選值列表

        Returns:
            套用篩選後的查詢物件
        """
        if not values:
            return query

        if hasattr(self.model, field_name):
            field = getattr(self.model, field_name)
            query = query.where(field.in_(values))

        return query

    def apply_date_range(
        self,
        query: Select,
        field_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Select:
        """
        應用日期範圍篩選

        Args:
            query: SQLAlchemy 查詢物件
            field_name: 日期欄位名稱
            start_date: 起始日期
            end_date: 結束日期

        Returns:
            套用篩選後的查詢物件
        """
        if not hasattr(self.model, field_name):
            return query

        field = getattr(self.model, field_name)

        if start_date:
            query = query.where(field >= start_date)

        if end_date:
            query = query.where(field <= end_date)

        return query

    def apply_sorting(
        self,
        query: Select,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
        default_sort: str = 'created_at'
    ) -> Select:
        """
        應用排序

        Args:
            query: SQLAlchemy 查詢物件
            sort_by: 排序欄位
            sort_order: 排序方向 ('asc' 或 'desc')
            default_sort: 預設排序欄位

        Returns:
            套用排序後的查詢物件
        """
        # 決定排序欄位
        field_name = sort_by if sort_by and hasattr(self.model, sort_by) else default_sort

        if not hasattr(self.model, field_name):
            return query

        field = getattr(self.model, field_name)

        # 套用排序方向
        if sort_order.lower() == 'asc':
            query = query.order_by(asc(field))
        else:
            query = query.order_by(desc(field))

        return query

    def apply_pagination(
        self,
        query: Select,
        page: int = 1,
        page_size: int = 20
    ) -> Select:
        """
        應用分頁

        Args:
            query: SQLAlchemy 查詢物件
            page: 頁碼（從 1 開始）
            page_size: 每頁筆數

        Returns:
            套用分頁後的查詢物件
        """
        # 確保有效的分頁參數
        page = max(1, page)
        page_size = max(1, min(100, page_size))  # 限制最大 100 筆

        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size)

    def apply_soft_delete_filter(
        self,
        query: Select,
        include_deleted: bool = False,
        deleted_field: str = 'is_deleted'
    ) -> Select:
        """
        應用軟刪除篩選

        Args:
            query: SQLAlchemy 查詢物件
            include_deleted: 是否包含已刪除的資料
            deleted_field: 刪除標記欄位名稱

        Returns:
            套用篩選後的查詢物件
        """
        if include_deleted:
            return query

        if hasattr(self.model, deleted_field):
            field = getattr(self.model, deleted_field)
            query = query.where(or_(field == False, field.is_(None)))

        return query


class PaginationHelper:
    """
    分頁助手

    提供統一的分頁回應包裝功能。
    """

    @staticmethod
    def wrap_response(
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> PaginatedResponse[T]:
        """
        包裝分頁回應

        Args:
            items: 資料列表
            total: 總筆數
            page: 當前頁碼
            page_size: 每頁筆數

        Returns:
            統一的分頁回應結構
        """
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            limit=page_size
        )

    @staticmethod
    def calculate_offset(page: int, page_size: int) -> int:
        """
        計算分頁偏移量

        Args:
            page: 頁碼（從 1 開始）
            page_size: 每頁筆數

        Returns:
            偏移量
        """
        return (max(1, page) - 1) * page_size

    @staticmethod
    def calculate_total_pages(total: int, page_size: int) -> int:
        """
        計算總頁數

        Args:
            total: 總筆數
            page_size: 每頁筆數

        Returns:
            總頁數
        """
        if page_size <= 0:
            return 0
        return ceil(total / page_size)

    @staticmethod
    def validate_pagination_params(
        page: int,
        page_size: int,
        max_page_size: int = 100
    ) -> tuple:
        """
        驗證並正規化分頁參數

        Args:
            page: 頁碼
            page_size: 每頁筆數
            max_page_size: 最大每頁筆數限制

        Returns:
            (正規化的 page, 正規化的 page_size)
        """
        validated_page = max(1, page)
        validated_page_size = max(1, min(max_page_size, page_size))
        return validated_page, validated_page_size


class FilterBuilder(Generic[ModelType]):
    """
    篩選條件建構器

    提供流暢的 API 來建構複雜的篩選條件。

    Usage:
        builder = FilterBuilder(Document)
        query = (builder
            .search('keyword', ['subject', 'content'])
            .date_range('doc_date', start, end)
            .exact('category', '收文')
            .sort('created_at', 'desc')
            .paginate(1, 20)
            .build(base_query))
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model
        self.helper = QueryHelper(model)
        self._operations: List[Callable[[Select], Select]] = []

    def search(
        self,
        keyword: Optional[str],
        fields: List[str],
        use_ilike: bool = True
    ) -> 'FilterBuilder':
        """添加搜尋條件"""
        if keyword:
            # 使用預設參數捕獲當前值，避免閉包變數捕獲問題
            self._operations.append(
                lambda q, kw=keyword, f=fields, ui=use_ilike: self.helper.apply_search(q, kw, f, ui)
            )
        return self

    def exact(self, field: str, value: Any) -> 'FilterBuilder':
        """添加精確匹配條件"""
        if value is not None:
            # 使用預設參數捕獲當前值
            self._operations.append(
                lambda q, f=field, v=value: self.helper.apply_exact_filter(q, f, v)
            )
        return self

    def in_list(self, field: str, values: Optional[List[Any]]) -> 'FilterBuilder':
        """添加 IN 條件"""
        if values:
            # 使用預設參數捕獲當前值
            self._operations.append(
                lambda q, f=field, v=values: self.helper.apply_in_filter(q, f, v)
            )
        return self

    def date_range(
        self,
        field: str,
        start: Optional[date] = None,
        end: Optional[date] = None
    ) -> 'FilterBuilder':
        """添加日期範圍條件"""
        if start or end:
            # 使用預設參數捕獲當前值
            self._operations.append(
                lambda q, f=field, s=start, e=end: self.helper.apply_date_range(q, f, s, e)
            )
        return self

    def sort(
        self,
        field: Optional[str] = None,
        order: str = 'desc',
        default: str = 'created_at'
    ) -> 'FilterBuilder':
        """添加排序"""
        # 使用預設參數捕獲當前值
        self._operations.append(
            lambda q, f=field, o=order, d=default: self.helper.apply_sorting(q, f, o, d)
        )
        return self

    def paginate(self, page: int = 1, page_size: int = 20) -> 'FilterBuilder':
        """添加分頁"""
        # 使用預設參數捕獲當前值
        self._operations.append(
            lambda q, p=page, ps=page_size: self.helper.apply_pagination(q, p, ps)
        )
        return self

    def exclude_deleted(self, deleted_field: str = 'is_deleted') -> 'FilterBuilder':
        """排除已刪除的資料"""
        # 使用預設參數捕獲當前值
        self._operations.append(
            lambda q, df=deleted_field: self.helper.apply_soft_delete_filter(q, False, df)
        )
        return self

    def build(self, query: Select) -> Select:
        """
        建構最終查詢

        Args:
            query: 基礎查詢物件

        Returns:
            套用所有條件後的查詢物件
        """
        for operation in self._operations:
            query = operation(query)
        return query

    def reset(self) -> 'FilterBuilder':
        """重置所有條件"""
        self._operations.clear()
        return self


# Re-export from split modules for backward compatibility
from app.services.base.statistics_helper import StatisticsHelper  # noqa: F401
from app.services.base.delete_check_helper import DeleteCheckHelper  # noqa: F401
