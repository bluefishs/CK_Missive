"""
DocumentQueryBuilder - 公文查詢建構器

使用流暢介面 (Fluent Interface) 模式，支援鏈式呼叫建構複雜查詢。

使用方式:
    documents = await (
        DocumentQueryBuilder(db)
        .with_status("待處理")
        .with_doc_type("收文")
        .with_date_range(start_date, end_date)
        .with_keyword("桃園")
        .order_by("doc_date", desc=True)
        .paginate(page=1, page_size=20)
        .execute()
    )

版本: 1.0.0
建立日期: 2026-02-06
參見: docs/SERVICE_ARCHITECTURE_STANDARDS.md
"""

import logging
from typing import List, Optional, TYPE_CHECKING
from datetime import date

from sqlalchemy import select, or_, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

if TYPE_CHECKING:
    from app.extended.models import OfficialDocument

logger = logging.getLogger(__name__)


class DocumentQueryBuilder:
    """
    公文查詢建構器

    提供流暢介面建構複雜查詢，減少重複的查詢組合邏輯。

    Example:
        # 基本查詢
        docs = await DocumentQueryBuilder(db).with_status("待處理").execute()

        # 複合查詢
        docs = await (
            DocumentQueryBuilder(db)
            .with_doc_type("收文")
            .with_status("待處理")
            .with_date_range(date(2026, 1, 1), date(2026, 1, 31))
            .with_keyword("會勘")
            .with_has_deadline()
            .order_by("deadline", desc=False)
            .paginate(page=1, page_size=20)
            .execute()
        )

        # 取得總數
        count = await (
            DocumentQueryBuilder(db)
            .with_status("待處理")
            .count()
        )
    """

    def __init__(self, db: AsyncSession):
        """
        初始化查詢建構器

        Args:
            db: AsyncSession 資料庫連線
        """
        from app.extended.models import OfficialDocument

        self.db = db
        self.model = OfficialDocument
        self._query: Select = select(OfficialDocument)
        self._conditions: List = []
        self._order_columns: List = []
        self._offset: Optional[int] = None
        self._limit: Optional[int] = None

    # =========================================================================
    # 狀態篩選
    # =========================================================================

    def with_status(self, status: str) -> 'DocumentQueryBuilder':
        """
        篩選指定狀態

        Args:
            status: 狀態值 (待處理/處理中/已結案/已歸檔)
        """
        self._conditions.append(self.model.status == status)
        return self

    def with_statuses(self, statuses: List[str]) -> 'DocumentQueryBuilder':
        """
        篩選多個狀態

        Args:
            statuses: 狀態值列表
        """
        self._conditions.append(self.model.status.in_(statuses))
        return self

    # =========================================================================
    # 類型篩選
    # =========================================================================

    def with_doc_type(self, doc_type: str) -> 'DocumentQueryBuilder':
        """
        篩選公文類型

        Args:
            doc_type: 收文/發文
        """
        self._conditions.append(self.model.doc_type == doc_type)
        return self

    def with_category(self, category: str) -> 'DocumentQueryBuilder':
        """
        篩選公文分類

        Args:
            category: 分類名稱
        """
        self._conditions.append(self.model.category == category)
        return self

    # =========================================================================
    # 日期篩選
    # =========================================================================

    def with_date_range(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> 'DocumentQueryBuilder':
        """
        篩選日期範圍

        Args:
            start_date: 起始日期
            end_date: 結束日期
        """
        if start_date:
            self._conditions.append(self.model.doc_date >= start_date)
        if end_date:
            self._conditions.append(self.model.doc_date <= end_date)
        return self

    def with_deadline_range(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> 'DocumentQueryBuilder':
        """
        篩選截止日期範圍

        Args:
            start_date: 起始日期
            end_date: 結束日期
        """
        if start_date:
            self._conditions.append(self.model.deadline >= start_date)
        if end_date:
            self._conditions.append(self.model.deadline <= end_date)
        return self

    def with_has_deadline(self, has_deadline: bool = True) -> 'DocumentQueryBuilder':
        """
        篩選有/無截止日期

        Args:
            has_deadline: True 篩選有截止日，False 篩選無截止日
        """
        if has_deadline:
            self._conditions.append(self.model.deadline.isnot(None))
        else:
            self._conditions.append(self.model.deadline.is_(None))
        return self

    def with_year(self, year: int) -> 'DocumentQueryBuilder':
        """
        篩選指定年度

        Args:
            year: 西元年份
        """
        from sqlalchemy import extract
        self._conditions.append(extract('year', self.model.doc_date) == year)
        return self

    # =========================================================================
    # 單位篩選
    # =========================================================================

    def with_sender(self, sender: str) -> 'DocumentQueryBuilder':
        """
        篩選發文單位

        Args:
            sender: 發文單位名稱
        """
        self._conditions.append(self.model.sender == sender)
        return self

    def with_sender_like(self, sender: str) -> 'DocumentQueryBuilder':
        """
        模糊篩選發文單位

        Args:
            sender: 發文單位關鍵字
        """
        self._conditions.append(self.model.sender.ilike(f"%{sender}%"))
        return self

    def with_receiver(self, receiver: str) -> 'DocumentQueryBuilder':
        """
        篩選受文單位

        Args:
            receiver: 受文單位名稱
        """
        self._conditions.append(self.model.receiver == receiver)
        return self

    def with_agency_id(self, agency_id: int) -> 'DocumentQueryBuilder':
        """
        篩選機關 ID（發文或受文）

        Args:
            agency_id: 機關 ID
        """
        self._conditions.append(
            or_(
                self.model.sender_agency_id == agency_id,
                self.model.receiver_agency_id == agency_id
            )
        )
        return self

    # =========================================================================
    # 關鍵字搜尋
    # =========================================================================

    def with_keyword(self, keyword: str) -> 'DocumentQueryBuilder':
        """
        關鍵字搜尋（主旨、公文字號、發文單位、備註）

        Args:
            keyword: 搜尋關鍵字
        """
        search_pattern = f"%{keyword}%"
        self._conditions.append(
            or_(
                self.model.subject.ilike(search_pattern),
                self.model.doc_number.ilike(search_pattern),
                self.model.sender.ilike(search_pattern),
                self.model.receiver.ilike(search_pattern),
                self.model.ck_note.ilike(search_pattern),
            )
        )
        return self

    def with_keyword_full(self, keyword: str) -> 'DocumentQueryBuilder':
        """
        全欄位關鍵字搜尋（含 content 欄位，供 AI 搜尋使用）

        Args:
            keyword: 搜尋關鍵字
        """
        search_pattern = f"%{keyword}%"
        self._conditions.append(
            or_(
                self.model.subject.ilike(search_pattern),
                self.model.doc_number.ilike(search_pattern),
                self.model.sender.ilike(search_pattern),
                self.model.receiver.ilike(search_pattern),
                self.model.content.ilike(search_pattern),
                self.model.ck_note.ilike(search_pattern),
            )
        )
        return self

    def with_keywords_full(self, keywords: List[str]) -> 'DocumentQueryBuilder':
        """
        多關鍵字全欄位搜尋（OR 邏輯，任一關鍵字命中即可）

        Args:
            keywords: 關鍵字列表
        """
        all_conditions = []
        for kw in keywords:
            pattern = f"%{kw}%"
            all_conditions.append(
                or_(
                    self.model.subject.ilike(pattern),
                    self.model.doc_number.ilike(pattern),
                    self.model.sender.ilike(pattern),
                    self.model.receiver.ilike(pattern),
                    self.model.content.ilike(pattern),
                    self.model.ck_note.ilike(pattern),
                )
            )
        if all_conditions:
            self._conditions.append(or_(*all_conditions))
        return self

    def with_keywords(self, keywords: List[str]) -> 'DocumentQueryBuilder':
        """
        多關鍵字搜尋（AND 邏輯）

        Args:
            keywords: 關鍵字列表
        """
        for keyword in keywords:
            self.with_keyword(keyword)
        return self

    def with_receiver_like(self, receiver: str) -> 'DocumentQueryBuilder':
        """
        模糊篩選受文單位

        Args:
            receiver: 受文單位關鍵字
        """
        self._conditions.append(self.model.receiver.ilike(f"%{receiver}%"))
        return self

    def with_contract_case(self, case_name: str) -> 'DocumentQueryBuilder':
        """
        篩選承攬案件（JOIN ContractProject）

        Args:
            case_name: 案件名稱關鍵字
        """
        from app.extended.models import ContractProject
        self._query = self._query.join(
            ContractProject,
            self.model.contract_project_id == ContractProject.id,
            isouter=True
        )
        self._conditions.append(
            ContractProject.project_name.ilike(f"%{case_name}%")
        )
        return self

    def with_assignee_access(self, user_name: str) -> 'DocumentQueryBuilder':
        """
        權限過濾：僅返回使用者可存取的公文

        Args:
            user_name: 使用者名稱
        """
        self._conditions.append(
            or_(
                self.model.assignee.ilike(f"%{user_name}%"),
                self.model.contract_project_id.is_(None),
            )
        )
        return self

    # =========================================================================
    # 其他篩選
    # =========================================================================

    def with_project_id(self, project_id: int) -> 'DocumentQueryBuilder':
        """
        篩選專案關聯

        Args:
            project_id: 專案 ID
        """
        self._conditions.append(self.model.contract_project_id == project_id)
        return self

    def with_has_attachment(
        self,
        has_attachment: bool = True
    ) -> 'DocumentQueryBuilder':
        """
        篩選有/無附件

        Args:
            has_attachment: True 篩選有附件，False 篩選無附件
        """
        self._conditions.append(self.model.has_attachment == has_attachment)
        return self

    # =========================================================================
    # 排序與分頁
    # =========================================================================

    def order_by(
        self,
        column: str,
        descending: bool = False
    ) -> 'DocumentQueryBuilder':
        """
        設定排序

        Args:
            column: 欄位名稱
            descending: 是否降冪排序
        """
        col = getattr(self.model, column, self.model.id)
        self._order_columns.append(desc(col) if descending else asc(col))
        return self

    def paginate(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> 'DocumentQueryBuilder':
        """
        設定分頁

        Args:
            page: 頁碼（從 1 開始）
            page_size: 每頁筆數
        """
        self._offset = (page - 1) * page_size
        self._limit = page_size
        return self

    def limit(self, limit: int) -> 'DocumentQueryBuilder':
        """
        設定筆數限制

        Args:
            limit: 最大筆數
        """
        self._limit = limit
        return self

    def offset(self, offset: int) -> 'DocumentQueryBuilder':
        """
        設定偏移量

        Args:
            offset: 跳過筆數
        """
        self._offset = offset
        return self

    # =========================================================================
    # 執行查詢
    # =========================================================================

    def _build_query(self) -> Select:
        """建構最終查詢"""
        query = self._query

        # 套用條件
        if self._conditions:
            query = query.where(and_(*self._conditions))

        # 套用排序
        if self._order_columns:
            query = query.order_by(*self._order_columns)
        else:
            # 預設按 id 降冪
            query = query.order_by(desc(self.model.id))

        # 套用分頁
        if self._offset is not None:
            query = query.offset(self._offset)
        if self._limit is not None:
            query = query.limit(self._limit)

        return query

    async def execute(self) -> List["OfficialDocument"]:
        """
        執行查詢並返回結果列表

        Returns:
            公文列表
        """
        query = self._build_query()
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def first(self) -> Optional["OfficialDocument"]:
        """
        執行查詢並返回第一筆結果

        Returns:
            公文物件或 None
        """
        self._limit = 1
        results = await self.execute()
        return results[0] if results else None

    async def count(self) -> int:
        """
        取得符合條件的總數

        Returns:
            總筆數
        """
        from sqlalchemy import func

        count_query = select(func.count(self.model.id))

        if self._conditions:
            count_query = count_query.where(and_(*self._conditions))

        result = await self.db.execute(count_query)
        return result.scalar() or 0

    async def exists(self) -> bool:
        """
        檢查是否存在符合條件的資料

        Returns:
            是否存在
        """
        return await self.count() > 0

    async def execute_with_count(self) -> tuple[List["OfficialDocument"], int]:
        """
        執行查詢並同時返回結果與總數

        Returns:
            (公文列表, 總數)
        """
        # 使用 asyncio.gather 並行執行
        import asyncio

        # 建立計數查詢器（不含分頁）
        count_builder = DocumentQueryBuilder(self.db)
        count_builder._conditions = self._conditions.copy()

        results, total = await asyncio.gather(
            self.execute(),
            count_builder.count()
        )

        return results, total
