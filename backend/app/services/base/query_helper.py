# -*- coding: utf-8 -*-
"""
統一查詢助手

提供統一的篩選、排序、搜尋邏輯，減少各服務中的重複代碼。
"""
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Generic
from datetime import date, datetime
from math import ceil

from sqlalchemy import Select, or_, and_, asc, desc, func
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
        conditions = []

        for field_name in search_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                if use_ilike:
                    conditions.append(field.ilike(f'%{keyword}%'))
                else:
                    conditions.append(field.like(f'%{keyword}%'))

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
        self._operations: List[callable] = []

    def search(
        self,
        keyword: Optional[str],
        fields: List[str],
        use_ilike: bool = True
    ) -> 'FilterBuilder':
        """添加搜尋條件"""
        if keyword:
            self._operations.append(
                lambda q: self.helper.apply_search(q, keyword, fields, use_ilike)
            )
        return self

    def exact(self, field: str, value: Any) -> 'FilterBuilder':
        """添加精確匹配條件"""
        if value is not None:
            self._operations.append(
                lambda q: self.helper.apply_exact_filter(q, field, value)
            )
        return self

    def in_list(self, field: str, values: Optional[List[Any]]) -> 'FilterBuilder':
        """添加 IN 條件"""
        if values:
            self._operations.append(
                lambda q: self.helper.apply_in_filter(q, field, values)
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
            self._operations.append(
                lambda q: self.helper.apply_date_range(q, field, start, end)
            )
        return self

    def sort(
        self,
        field: Optional[str] = None,
        order: str = 'desc',
        default: str = 'created_at'
    ) -> 'FilterBuilder':
        """添加排序"""
        self._operations.append(
            lambda q: self.helper.apply_sorting(q, field, order, default)
        )
        return self

    def paginate(self, page: int = 1, page_size: int = 20) -> 'FilterBuilder':
        """添加分頁"""
        self._operations.append(
            lambda q: self.helper.apply_pagination(q, page, page_size)
        )
        return self

    def exclude_deleted(self, deleted_field: str = 'is_deleted') -> 'FilterBuilder':
        """排除已刪除的資料"""
        self._operations.append(
            lambda q: self.helper.apply_soft_delete_filter(q, False, deleted_field)
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


class StatisticsHelper:
    """
    統計助手

    提供統一的統計查詢功能，減少各服務中的重複統計代碼。

    Usage:
        stats = await StatisticsHelper.get_basic_stats(db, MyModel)
        group_stats = await StatisticsHelper.get_grouped_stats(
            db, MyModel, 'status', MyModel.id
        )
    """

    @staticmethod
    async def get_basic_stats(
        db: AsyncSession,
        model: Type[ModelType],
        count_field: Any = None
    ) -> Dict[str, int]:
        """
        取得基本統計資料（總數）

        Args:
            db: 資料庫 session
            model: SQLAlchemy 模型類
            count_field: 計數欄位（預設使用模型的 id）

        Returns:
            包含 total 的字典
        """
        if count_field is None:
            count_field = model.id if hasattr(model, 'id') else func.count()

        query = select(func.count(count_field))
        result = await db.execute(query)
        total = result.scalar_one()

        return {"total": total}

    @staticmethod
    async def get_grouped_stats(
        db: AsyncSession,
        model: Type[ModelType],
        group_field_name: str,
        count_field: Any = None,
        filter_condition: Any = None
    ) -> Dict[str, int]:
        """
        取得分組統計資料

        Args:
            db: 資料庫 session
            model: SQLAlchemy 模型類
            group_field_name: 分組欄位名稱
            count_field: 計數欄位（預設使用模型的 id）
            filter_condition: 可選的篩選條件

        Returns:
            {group_value: count} 的字典
        """
        if not hasattr(model, group_field_name):
            return {}

        group_field = getattr(model, group_field_name)
        if count_field is None:
            count_field = model.id if hasattr(model, 'id') else func.count()

        query = select(
            group_field,
            func.count(count_field).label('count')
        ).group_by(group_field)

        if filter_condition is not None:
            query = query.where(filter_condition)

        result = await db.execute(query)
        rows = result.all()

        return {str(row[0]) if row[0] else 'null': row[1] for row in rows}

    @staticmethod
    async def get_date_range_stats(
        db: AsyncSession,
        model: Type[ModelType],
        date_field_name: str,
        count_field: Any = None,
        filter_condition: Any = None
    ) -> Dict[str, Any]:
        """
        取得日期範圍統計

        Args:
            db: 資料庫 session
            model: SQLAlchemy 模型類
            date_field_name: 日期欄位名稱
            count_field: 計數欄位
            filter_condition: 可選的篩選條件

        Returns:
            包含 min_date, max_date, total 的字典
        """
        if not hasattr(model, date_field_name):
            return {"min_date": None, "max_date": None, "total": 0}

        date_field = getattr(model, date_field_name)
        if count_field is None:
            count_field = model.id if hasattr(model, 'id') else func.count()

        query = select(
            func.min(date_field).label('min_date'),
            func.max(date_field).label('max_date'),
            func.count(count_field).label('total')
        )

        if filter_condition is not None:
            query = query.where(filter_condition)

        result = await db.execute(query)
        row = result.one()

        return {
            "min_date": row.min_date,
            "max_date": row.max_date,
            "total": row.total
        }


class DeleteCheckHelper:
    """
    刪除檢查助手

    提供統一的刪除前關聯檢查功能。

    Usage:
        can_delete, count = await DeleteCheckHelper.check_usage(
            db, OfficialDocument, 'sender_agency_id', agency_id
        )
        if not can_delete:
            raise ResourceInUseException(f"機關", f"仍有 {count} 筆公文關聯")
    """

    @staticmethod
    async def check_usage(
        db: AsyncSession,
        related_model: Type[ModelType],
        foreign_key_field: str,
        entity_id: int
    ) -> Tuple[bool, int]:
        """
        檢查實體是否被其他資料使用

        Args:
            db: 資料庫 session
            related_model: 關聯模型類
            foreign_key_field: 外鍵欄位名稱
            entity_id: 要檢查的實體 ID

        Returns:
            (可否刪除, 使用計數) 的元組
        """
        if not hasattr(related_model, foreign_key_field):
            return True, 0

        fk_field = getattr(related_model, foreign_key_field)
        id_field = related_model.id if hasattr(related_model, 'id') else None

        if id_field is None:
            return True, 0

        query = select(func.count(id_field)).where(fk_field == entity_id)
        result = await db.execute(query)
        count = result.scalar_one()

        return count == 0, count

    @staticmethod
    async def check_multiple_usages(
        db: AsyncSession,
        related_model: Type[ModelType],
        checks: List[Tuple[str, int]]
    ) -> Tuple[bool, int]:
        """
        檢查多個外鍵欄位的使用情況（OR 邏輯）

        Args:
            db: 資料庫 session
            related_model: 關聯模型類
            checks: [(欄位名, 實體ID), ...] 的列表

        Returns:
            (可否刪除, 總使用計數) 的元組

        Example:
            # 檢查機關是否作為發文或收文單位
            can_delete, count = await DeleteCheckHelper.check_multiple_usages(
                db, OfficialDocument,
                [('sender_agency_id', agency_id), ('receiver_agency_id', agency_id)]
            )
        """
        conditions = []
        for field_name, entity_id in checks:
            if hasattr(related_model, field_name):
                field = getattr(related_model, field_name)
                conditions.append(field == entity_id)

        if not conditions:
            return True, 0

        id_field = related_model.id if hasattr(related_model, 'id') else None
        if id_field is None:
            return True, 0

        query = select(func.count(id_field)).where(or_(*conditions))
        result = await db.execute(query)
        count = result.scalar_one()

        return count == 0, count
