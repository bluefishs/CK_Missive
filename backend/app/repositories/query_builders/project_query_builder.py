"""
ProjectQueryBuilder - 專案查詢建構器

使用流暢介面 (Fluent Interface) 模式，支援鏈式呼叫建構複雜查詢。

使用方式:
    projects = await (
        ProjectQueryBuilder(db)
        .with_status("進行中")
        .with_year(2026)
        .with_user_access(user_id)
        .with_keyword("桃園")
        .order_by("contract_date", desc=True)
        .paginate(page=1, page_size=20)
        .execute()
    )

版本: 1.0.0
建立日期: 2026-02-06
"""

import logging
from typing import List, Optional, TYPE_CHECKING
from datetime import date

from sqlalchemy import select, or_, and_, desc, asc, exists as sql_exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

if TYPE_CHECKING:
    from app.extended.models import ContractProject

logger = logging.getLogger(__name__)


class ProjectQueryBuilder:
    """
    專案查詢建構器

    提供流暢介面建構複雜查詢。

    Example:
        # 基本查詢
        projects = await ProjectQueryBuilder(db).with_status("進行中").execute()

        # 複合查詢
        projects = await (
            ProjectQueryBuilder(db)
            .with_status("進行中")
            .with_year(2026)
            .with_keyword("會勘")
            .with_user_access(current_user.id)
            .order_by("contract_date", desc=True)
            .paginate(page=1, page_size=20)
            .execute()
        )
    """

    def __init__(self, db: AsyncSession):
        """初始化查詢建構器"""
        from app.extended.models import ContractProject

        self.db = db
        self.model = ContractProject
        self._query: Select = select(ContractProject)
        self._conditions: List = []
        self._order_columns: List = []
        self._offset: Optional[int] = None
        self._limit: Optional[int] = None

    # =========================================================================
    # 狀態篩選
    # =========================================================================

    def with_status(self, status: str) -> 'ProjectQueryBuilder':
        """篩選指定狀態 (進行中/已完成/暫停)"""
        self._conditions.append(self.model.status == status)
        return self

    def with_statuses(self, statuses: List[str]) -> 'ProjectQueryBuilder':
        """篩選多個狀態"""
        self._conditions.append(self.model.status.in_(statuses))
        return self

    def active_only(self) -> 'ProjectQueryBuilder':
        """只顯示進行中的專案"""
        return self.with_status("進行中")

    # =========================================================================
    # 年度篩選
    # =========================================================================

    def with_year(self, year: int) -> 'ProjectQueryBuilder':
        """篩選指定年度"""
        self._conditions.append(self.model.year == year)
        return self

    def with_years(self, years: List[int]) -> 'ProjectQueryBuilder':
        """篩選多個年度"""
        self._conditions.append(self.model.year.in_(years))
        return self

    # =========================================================================
    # 日期篩選
    # =========================================================================

    def with_contract_date_range(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> 'ProjectQueryBuilder':
        """篩選合約日期範圍"""
        if start_date:
            self._conditions.append(self.model.contract_date >= start_date)
        if end_date:
            self._conditions.append(self.model.contract_date <= end_date)
        return self

    # =========================================================================
    # 關聯篩選
    # =========================================================================

    def with_vendor_id(self, vendor_id: int) -> 'ProjectQueryBuilder':
        """篩選關聯特定廠商的專案"""
        from app.extended.models import project_vendor_association

        subquery = (
            select(project_vendor_association.c.project_id)
            .where(project_vendor_association.c.vendor_id == vendor_id)
        )
        self._conditions.append(self.model.id.in_(subquery))
        return self

    def with_user_access(self, user_id: int, is_admin: bool = False) -> 'ProjectQueryBuilder':
        """
        篩選使用者有權限存取的專案 (RLS)

        Args:
            user_id: 使用者 ID
            is_admin: 是否為管理員（管理員可看所有專案）
        """
        if is_admin:
            return self

        from app.extended.models import project_user_assignment

        subquery = (
            select(project_user_assignment.c.project_id)
            .where(project_user_assignment.c.user_id == user_id)
        )
        self._conditions.append(self.model.id.in_(subquery))
        return self

    # =========================================================================
    # 關鍵字搜尋
    # =========================================================================

    def with_keyword(self, keyword: str) -> 'ProjectQueryBuilder':
        """關鍵字搜尋（專案名稱、專案編號、備註）"""
        search_pattern = f"%{keyword}%"
        self._conditions.append(
            or_(
                self.model.project_name.ilike(search_pattern),
                self.model.project_code.ilike(search_pattern),
                self.model.notes.ilike(search_pattern),
            )
        )
        return self

    def with_project_code(self, project_code: str) -> 'ProjectQueryBuilder':
        """精確匹配專案編號"""
        self._conditions.append(self.model.project_code == project_code)
        return self

    # =========================================================================
    # 金額篩選
    # =========================================================================

    def with_contract_amount_range(
        self,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None
    ) -> 'ProjectQueryBuilder':
        """篩選合約金額範圍"""
        if min_amount is not None:
            self._conditions.append(self.model.contract_amount >= min_amount)
        if max_amount is not None:
            self._conditions.append(self.model.contract_amount <= max_amount)
        return self

    # =========================================================================
    # 排序與分頁
    # =========================================================================

    def order_by(
        self,
        column: str,
        descending: bool = False
    ) -> 'ProjectQueryBuilder':
        """設定排序"""
        col = getattr(self.model, column, self.model.id)
        self._order_columns.append(desc(col) if descending else asc(col))
        return self

    def paginate(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> 'ProjectQueryBuilder':
        """設定分頁"""
        self._offset = (page - 1) * page_size
        self._limit = page_size
        return self

    def limit(self, limit: int) -> 'ProjectQueryBuilder':
        """設定筆數限制"""
        self._limit = limit
        return self

    # =========================================================================
    # 執行查詢
    # =========================================================================

    def _build_query(self) -> Select:
        """建構最終查詢"""
        query = self._query

        if self._conditions:
            query = query.where(and_(*self._conditions))

        if self._order_columns:
            query = query.order_by(*self._order_columns)
        else:
            query = query.order_by(desc(self.model.id))

        if self._offset is not None:
            query = query.offset(self._offset)
        if self._limit is not None:
            query = query.limit(self._limit)

        return query

    async def execute(self) -> List["ContractProject"]:
        """執行查詢並返回結果列表"""
        query = self._build_query()
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def first(self) -> Optional["ContractProject"]:
        """執行查詢並返回第一筆結果"""
        self._limit = 1
        results = await self.execute()
        return results[0] if results else None

    async def count(self) -> int:
        """取得符合條件的總數"""
        from sqlalchemy import func

        count_query = select(func.count(self.model.id))
        if self._conditions:
            count_query = count_query.where(and_(*self._conditions))

        result = await self.db.execute(count_query)
        return result.scalar() or 0

    async def exists(self) -> bool:
        """檢查是否存在符合條件的資料"""
        return await self.count() > 0

    async def execute_with_count(self) -> tuple[List["ContractProject"], int]:
        """執行查詢並同時返回結果與總數"""
        import asyncio

        count_builder = ProjectQueryBuilder(self.db)
        count_builder._conditions = self._conditions.copy()

        results, total = await asyncio.gather(
            self.execute(),
            count_builder.count()
        )

        return results, total
