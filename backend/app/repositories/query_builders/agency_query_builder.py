"""
AgencyQueryBuilder - 機關查詢建構器

使用流暢介面 (Fluent Interface) 模式，支援鏈式呼叫建構複雜查詢。

使用方式:
    agencies = await (
        AgencyQueryBuilder(db)
        .with_type("市政府")
        .with_keyword("桃園")
        .order_by("agency_name")
        .paginate(page=1, page_size=20)
        .execute()
    )

版本: 1.0.0
建立日期: 2026-02-06
"""

import logging
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import select, or_, and_, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

if TYPE_CHECKING:
    from app.extended.models import GovernmentAgency

logger = logging.getLogger(__name__)


class AgencyQueryBuilder:
    """
    機關查詢建構器

    提供流暢介面建構複雜查詢。

    Example:
        # 基本查詢
        agencies = await AgencyQueryBuilder(db).with_type("市政府").execute()

        # 複合查詢
        agencies = await (
            AgencyQueryBuilder(db)
            .with_type("區公所")
            .with_keyword("中壢")
            .with_has_documents()
            .order_by("agency_name")
            .paginate(page=1, page_size=20)
            .execute()
        )
    """

    def __init__(self, db: AsyncSession):
        """初始化查詢建構器"""
        from app.extended.models import GovernmentAgency

        self.db = db
        self.model = GovernmentAgency
        self._query: Select = select(GovernmentAgency)
        self._conditions: List = []
        self._order_columns: List = []
        self._offset: Optional[int] = None
        self._limit: Optional[int] = None

    # =========================================================================
    # 類型篩選
    # =========================================================================

    def with_type(self, agency_type: str) -> 'AgencyQueryBuilder':
        """篩選機關類型"""
        self._conditions.append(self.model.agency_type == agency_type)
        return self

    def with_types(self, types: List[str]) -> 'AgencyQueryBuilder':
        """篩選多個類型"""
        self._conditions.append(self.model.agency_type.in_(types))
        return self

    # =========================================================================
    # 關鍵字搜尋
    # =========================================================================

    def with_keyword(self, keyword: str) -> 'AgencyQueryBuilder':
        """關鍵字搜尋（機關名稱、簡稱、代碼）"""
        search_pattern = f"%{keyword}%"
        self._conditions.append(
            or_(
                self.model.agency_name.ilike(search_pattern),
                self.model.agency_short_name.ilike(search_pattern),
                self.model.agency_code.ilike(search_pattern),
            )
        )
        return self

    def with_name(self, name: str) -> 'AgencyQueryBuilder':
        """精確匹配機關名稱"""
        self._conditions.append(self.model.agency_name == name)
        return self

    def with_name_like(self, name: str) -> 'AgencyQueryBuilder':
        """模糊匹配機關名稱"""
        self._conditions.append(self.model.agency_name.ilike(f"%{name}%"))
        return self

    def with_short_name(self, short_name: str) -> 'AgencyQueryBuilder':
        """精確匹配機關簡稱"""
        self._conditions.append(self.model.agency_short_name == short_name)
        return self

    def with_code(self, code: str) -> 'AgencyQueryBuilder':
        """精確匹配機關代碼"""
        self._conditions.append(self.model.agency_code == code)
        return self

    # =========================================================================
    # 公文關聯篩選
    # =========================================================================

    def with_has_documents(self) -> 'AgencyQueryBuilder':
        """只顯示有關聯公文的機關"""
        from app.extended.models import OfficialDocument

        # 發文或受文
        sender_subquery = (
            select(OfficialDocument.sender_agency_id)
            .where(OfficialDocument.sender_agency_id.isnot(None))
            .distinct()
        )
        receiver_subquery = (
            select(OfficialDocument.receiver_agency_id)
            .where(OfficialDocument.receiver_agency_id.isnot(None))
            .distinct()
        )

        self._conditions.append(
            or_(
                self.model.id.in_(sender_subquery),
                self.model.id.in_(receiver_subquery)
            )
        )
        return self

    def with_document_count_above(self, min_count: int) -> 'AgencyQueryBuilder':
        """篩選公文數量超過指定值的機關"""
        from app.extended.models import OfficialDocument

        # 計算發文+受文數量
        subquery = (
            select(OfficialDocument.sender_agency_id.label('agency_id'))
            .where(OfficialDocument.sender_agency_id.isnot(None))
            .union_all(
                select(OfficialDocument.receiver_agency_id.label('agency_id'))
                .where(OfficialDocument.receiver_agency_id.isnot(None))
            )
            .subquery()
        )

        count_subquery = (
            select(subquery.c.agency_id)
            .group_by(subquery.c.agency_id)
            .having(func.count() >= min_count)
        )

        self._conditions.append(self.model.id.in_(count_subquery))
        return self

    # =========================================================================
    # 排序與分頁
    # =========================================================================

    def order_by(
        self,
        column: str,
        descending: bool = False
    ) -> 'AgencyQueryBuilder':
        """設定排序"""
        col = getattr(self.model, column, self.model.id)
        self._order_columns.append(desc(col) if descending else asc(col))
        return self

    def order_by_name(self) -> 'AgencyQueryBuilder':
        """按機關名稱排序"""
        return self.order_by('agency_name', descending=False)

    def paginate(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> 'AgencyQueryBuilder':
        """設定分頁"""
        self._offset = (page - 1) * page_size
        self._limit = page_size
        return self

    def limit(self, limit: int) -> 'AgencyQueryBuilder':
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
            query = query.order_by(self.model.agency_name)

        if self._offset is not None:
            query = query.offset(self._offset)
        if self._limit is not None:
            query = query.limit(self._limit)

        return query

    async def execute(self) -> List["GovernmentAgency"]:
        """執行查詢並返回結果列表"""
        query = self._build_query()
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def first(self) -> Optional["GovernmentAgency"]:
        """執行查詢並返回第一筆結果"""
        self._limit = 1
        results = await self.execute()
        return results[0] if results else None

    async def count(self) -> int:
        """取得符合條件的總數"""
        count_query = select(func.count(self.model.id))
        if self._conditions:
            count_query = count_query.where(and_(*self._conditions))

        result = await self.db.execute(count_query)
        return result.scalar() or 0

    async def exists(self) -> bool:
        """檢查是否存在符合條件的資料"""
        return await self.count() > 0

    async def execute_with_count(self) -> tuple[List["GovernmentAgency"], int]:
        """執行查詢並同時返回結果與總數"""
        import asyncio

        count_builder = AgencyQueryBuilder(self.db)
        count_builder._conditions = self._conditions.copy()

        results, total = await asyncio.gather(
            self.execute(),
            count_builder.count()
        )

        return results, total

    # =========================================================================
    # 智慧匹配
    # =========================================================================

    async def match_by_name(
        self,
        name: str,
        threshold: float = 0.7
    ) -> List[tuple["GovernmentAgency", float]]:
        """
        根據名稱進行模糊匹配並返回相似度分數

        Args:
            name: 要匹配的名稱
            threshold: 最低相似度閾值 (0-1)

        Returns:
            (機關, 相似度) 的列表，按相似度降序
        """
        # 簡單的字串匹配策略
        all_agencies = await self.execute()
        matches = []

        for agency in all_agencies:
            # 精確匹配
            if agency.agency_name == name:
                matches.append((agency, 1.0))
                continue

            # 簡稱匹配
            if agency.agency_short_name and agency.agency_short_name == name:
                matches.append((agency, 0.95))
                continue

            # 包含匹配
            name_lower = name.lower()
            agency_name_lower = agency.agency_name.lower()

            if name_lower in agency_name_lower:
                score = len(name_lower) / len(agency_name_lower)
                if score >= threshold:
                    matches.append((agency, score))
            elif agency_name_lower in name_lower:
                score = len(agency_name_lower) / len(name_lower)
                if score >= threshold:
                    matches.append((agency, score))

        # 按相似度降序排列
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
