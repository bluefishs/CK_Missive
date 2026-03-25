"""
DocumentRepository - 公文資料存取層

提供公文相關的資料庫查詢操作，包含：
- 公文特定查詢方法
- 附件關聯查詢
- 進階篩選
- 投影查詢最佳化 (v1.1.0)

統計方法已提取至 DocumentStatsRepository (v1.2.0)

版本: 1.1.0
建立日期: 2026-01-26
更新日期: 2026-02-04
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract, desc, asc
from sqlalchemy.orm import selectinload, joinedload

from app.repositories.base_repository import BaseRepository
from app.extended.models import (
    OfficialDocument,
    DocumentAttachment,
    DocumentCalendarEvent,
    ContractProject,
    GovernmentAgency,
)

logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository[OfficialDocument]):
    """
    公文資料存取層

    繼承 BaseRepository 並擴展公文特定的查詢方法。

    Example:
        doc_repo = DocumentRepository(db)

        # 基本查詢
        doc = await doc_repo.get_by_id(1)

        # 公文特定查詢
        pending = await doc_repo.get_by_status('pending')
        incoming = await doc_repo.get_incoming_documents(year=2026)

        # 投影查詢（效能優化）
        docs = await doc_repo.get_list_projected(
            page=1, page_size=20, doc_type='收文'
        )
    """

    # 搜尋欄位設定
    SEARCH_FIELDS = ['subject', 'doc_number', 'sender', 'receiver', 'content', 'notes', 'ck_note']

    # 列表頁面投影欄位（僅載入必要欄位，減少約 30% 資料傳輸）
    LIST_PROJECTION_FIELDS = [
        'id',
        'doc_number',
        'subject',
        'doc_type',
        'category',
        'status',
        'doc_date',
        'receive_date',
        'deadline',
        'sender',
        'receiver',
        'auto_serial',
        'has_attachment',
        'contract_project_id',
        'sender_agency_id',
        'receiver_agency_id',
        'created_at',
    ]

    # 摘要投影欄位（最小化，用於下拉選單等）
    SUMMARY_PROJECTION_FIELDS = [
        'id',
        'doc_number',
        'subject',
        'doc_type',
        'doc_date',
    ]

    def __init__(self, db: AsyncSession):
        """
        初始化公文 Repository

        Args:
            db: AsyncSession 資料庫連線
        """
        super().__init__(db, OfficialDocument)

    # =========================================================================
    # 公文特定查詢方法
    # =========================================================================

    async def get_by_doc_number(self, doc_number: str) -> Optional[OfficialDocument]:
        """
        根據公文文號取得公文

        Args:
            doc_number: 公文文號

        Returns:
            公文實體，若不存在則返回 None
        """
        return await self.find_one_by(doc_number=doc_number)

    async def get_by_auto_serial(self, auto_serial: str) -> Optional[OfficialDocument]:
        """
        根據流水序號取得公文

        Args:
            auto_serial: 流水序號 (如 R0001, S0001)

        Returns:
            公文實體，若不存在則返回 None
        """
        return await self.find_one_by(auto_serial=auto_serial)

    async def get_recent(self, limit: int = 10) -> List[OfficialDocument]:
        """
        取得最近建立的公文

        Args:
            limit: 筆數上限

        Returns:
            按 created_at 降序排列的公文列表
        """
        query = (
            select(OfficialDocument)
            .order_by(OfficialDocument.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_project_ids(
        self,
        project_ids: List[int],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        根據專案 ID 列表取得關聯公文摘要

        Args:
            project_ids: 專案 ID 列表
            limit: 取得筆數上限

        Returns:
            公文摘要字典列表
        """
        if not project_ids:
            return []
        query = (
            select(
                OfficialDocument.id,
                OfficialDocument.doc_number,
                OfficialDocument.subject,
                OfficialDocument.doc_type,
                OfficialDocument.doc_date,
            )
            .where(OfficialDocument.contract_project_id.in_(project_ids))
            .order_by(OfficialDocument.doc_date.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return [
            {
                "id": row.id,
                "doc_number": row.doc_number,
                "subject": row.subject,
                "doc_type": row.doc_type,
                "doc_date": str(row.doc_date) if row.doc_date else None,
            }
            for row in result.all()
        ]

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        根據處理狀態取得公文列表

        Args:
            status: 處理狀態 (待處理, 處理中, 已辦畢)
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            公文列表
        """
        query = (
            select(OfficialDocument)
            .where(OfficialDocument.status == status)
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_type(
        self,
        doc_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        根據公文類型取得公文列表

        Args:
            doc_type: 公文類型 (收文/發文)
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            公文列表
        """
        query = (
            select(OfficialDocument)
            .where(OfficialDocument.doc_type == doc_type)
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_incoming_documents(
        self,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        取得收文列表

        Args:
            year: 年度（可選）
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            收文列表
        """
        query = select(OfficialDocument).where(
            OfficialDocument.doc_type == '收文'
        )

        if year:
            query = query.where(
                extract('year', OfficialDocument.receive_date) == year
            )

        query = query.order_by(desc(OfficialDocument.receive_date)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_outgoing_documents(
        self,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        取得發文列表

        Args:
            year: 年度（可選）
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            發文列表
        """
        query = select(OfficialDocument).where(
            OfficialDocument.doc_type == '發文'
        )

        if year:
            query = query.where(
                extract('year', OfficialDocument.doc_date) == year
            )

        query = query.order_by(desc(OfficialDocument.doc_date)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        doc_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        根據日期範圍取得公文列表

        Args:
            start_date: 開始日期
            end_date: 結束日期
            doc_type: 公文類型（可選）
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            公文列表
        """
        query = select(OfficialDocument).where(
            and_(
                OfficialDocument.doc_date >= start_date,
                OfficialDocument.doc_date <= end_date
            )
        )

        if doc_type:
            query = query.where(OfficialDocument.doc_type == doc_type)

        query = query.order_by(desc(OfficialDocument.doc_date)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_project(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        根據專案 ID 取得關聯公文

        Args:
            project_id: 專案 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            公文列表
        """
        query = (
            select(OfficialDocument)
            .where(OfficialDocument.contract_project_id == project_id)
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_agency(
        self,
        agency_id: int,
        as_sender: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        根據機關 ID 取得相關公文

        Args:
            agency_id: 機關 ID
            as_sender: True=作為發文機關, False=作為受文機關
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            公文列表
        """
        if as_sender:
            condition = OfficialDocument.sender_agency_id == agency_id
        else:
            condition = OfficialDocument.receiver_agency_id == agency_id

        query = (
            select(OfficialDocument)
            .where(condition)
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 附件關聯查詢
    # =========================================================================

    async def get_with_attachments(self, id: int) -> Optional[OfficialDocument]:
        """
        取得公文含附件

        Args:
            id: 公文 ID

        Returns:
            公文實體（含 attachments 關聯）
        """
        return await self.get_by_id_with_relations(id, ['attachments'])

    async def get_with_all_relations(self, id: int) -> Optional[OfficialDocument]:
        """
        取得公文含所有關聯

        Args:
            id: 公文 ID

        Returns:
            公文實體（含所有關聯）
        """
        return await self.get_by_id_with_relations(
            id,
            ['attachments', 'calendar_events', 'contract_project', 'sender_agency', 'receiver_agency']
        )

    async def get_attachments(self, document_id: int) -> List[DocumentAttachment]:
        """
        取得公文的所有附件

        Args:
            document_id: 公文 ID

        Returns:
            附件列表
        """
        query = (
            select(DocumentAttachment)
            .where(DocumentAttachment.document_id == document_id)
            .order_by(DocumentAttachment.created_at)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_attachment_count(self, document_id: int) -> int:
        """
        取得公文的附件數量

        Args:
            document_id: 公文 ID

        Returns:
            附件數量
        """
        query = select(func.count(DocumentAttachment.id)).where(
            DocumentAttachment.document_id == document_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_documents_with_attachments(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[OfficialDocument]:
        """
        取得有附件的公文列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            公文列表
        """
        query = (
            select(OfficialDocument)
            .where(OfficialDocument.has_attachment == True)
            .options(selectinload(OfficialDocument.attachments))
            .order_by(desc(OfficialDocument.doc_date))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 行事曆事件查詢
    # =========================================================================

    async def get_calendar_events(
        self,
        document_id: int
    ) -> List[DocumentCalendarEvent]:
        """
        取得公文的行事曆事件

        Args:
            document_id: 公文 ID

        Returns:
            行事曆事件列表
        """
        query = (
            select(DocumentCalendarEvent)
            .where(DocumentCalendarEvent.document_id == document_id)
            .order_by(DocumentCalendarEvent.start_date)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_documents_with_upcoming_events(
        self,
        days_ahead: int = 7
    ) -> List[OfficialDocument]:
        """
        取得有即將到期事件的公文

        Args:
            days_ahead: 未來幾天內

        Returns:
            公文列表
        """
        from datetime import timedelta
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        query = (
            select(OfficialDocument)
            .join(DocumentCalendarEvent)
            .where(
                and_(
                    DocumentCalendarEvent.start_date >= today,
                    DocumentCalendarEvent.start_date <= end_date
                )
            )
            .options(selectinload(OfficialDocument.calendar_events))
            .distinct()
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 流水序號相關
    # =========================================================================

    async def get_next_serial_number(
        self,
        doc_type: str,
        year: Optional[int] = None
    ) -> str:
        """
        取得下一個流水序號

        Args:
            doc_type: 公文類型 (收文/發文)
            year: 年度（預設當年）

        Returns:
            下一個流水序號 (如 R0001, S0001)
        """
        if year is None:
            year = date.today().year

        prefix = 'R' if doc_type == '收文' else 'S'
        pattern = f"{prefix}%"

        # 查詢當年度最大序號
        query = (
            select(func.max(OfficialDocument.auto_serial))
            .where(
                and_(
                    OfficialDocument.auto_serial.like(pattern),
                    extract('year', OfficialDocument.created_at) == year
                )
            )
        )
        result = await self.db.execute(query)
        max_serial = result.scalar()

        if max_serial:
            # 解析現有序號，加 1
            try:
                current_num = int(max_serial[1:])
                next_num = current_num + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}{next_num:04d}"

    async def check_serial_exists(self, auto_serial: str) -> bool:
        """
        檢查流水序號是否已存在

        Args:
            auto_serial: 流水序號

        Returns:
            是否存在
        """
        return await self.exists_by(auto_serial=auto_serial)

    # =========================================================================
    # 進階篩選
    # =========================================================================

    async def filter_documents(
        self,
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        project_id: Optional[int] = None,
        sender_agency_id: Optional[int] = None,
        receiver_agency_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = 'doc_date',
        sort_order: str = 'desc'
    ) -> Tuple[List[OfficialDocument], int]:
        """
        進階篩選公文

        Args:
            doc_type: 公文類型
            status: 處理狀態
            category: 收發文分類
            project_id: 專案 ID
            sender_agency_id: 發文機關 ID
            receiver_agency_id: 受文機關 ID
            start_date: 開始日期
            end_date: 結束日期
            search: 搜尋關鍵字
            skip: 跳過筆數
            limit: 取得筆數
            sort_by: 排序欄位
            sort_order: 排序方向

        Returns:
            (公文列表, 總數) 元組
        """
        query = select(OfficialDocument)

        # N+1 優化：預載入附件關聯，避免迴圈存取時逐筆查詢
        query = query.options(selectinload(OfficialDocument.attachments))

        conditions = []

        # 套用篩選條件
        if doc_type:
            conditions.append(OfficialDocument.doc_type == doc_type)
        if status:
            conditions.append(OfficialDocument.status == status)
        if category:
            conditions.append(OfficialDocument.category == category)
        if project_id:
            conditions.append(OfficialDocument.contract_project_id == project_id)
        if sender_agency_id:
            conditions.append(OfficialDocument.sender_agency_id == sender_agency_id)
        if receiver_agency_id:
            conditions.append(OfficialDocument.receiver_agency_id == receiver_agency_id)
        if start_date:
            conditions.append(OfficialDocument.doc_date >= start_date)
        if end_date:
            conditions.append(OfficialDocument.doc_date <= end_date)

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            search_conditions = [
                getattr(OfficialDocument, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(OfficialDocument, field)
            ]
            if search_conditions:
                conditions.append(or_(*search_conditions))

        if conditions:
            query = query.where(and_(*conditions))

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 排序
        sort_column = getattr(OfficialDocument, sort_by, OfficialDocument.doc_date)
        if sort_order.lower() == 'asc':
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # 分頁
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        documents = list(result.scalars().all())

        return documents, total

    # =========================================================================
    # 投影查詢方法 (Projection Query) - v1.1.0
    # =========================================================================

    async def get_list_projected(
        self,
        page: int = 1,
        page_size: int = 20,
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        project_id: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: str = 'doc_date',
        sort_order: str = 'desc'
    ) -> Dict[str, Any]:
        """
        取得公文列表（投影查詢）- 效能優化版

        使用投影查詢僅載入 LIST_PROJECTION_FIELDS 定義的欄位，
        減少約 30% 的資料傳輸量，特別適用於列表頁面。

        Args:
            page: 頁碼（從 1 開始）
            page_size: 每頁筆數
            doc_type: 公文類型篩選
            status: 狀態篩選
            category: 收發文分類篩選
            project_id: 專案 ID 篩選
            search: 搜尋關鍵字
            sort_by: 排序欄位
            sort_order: 排序方向 (asc/desc)

        Returns:
            包含 items, total, page, page_size, total_pages 的字典

        Example:
            result = await doc_repo.get_list_projected(
                page=1, page_size=20,
                doc_type='收文', status='待處理'
            )
        """
        # 建構篩選條件
        conditions = []
        if doc_type:
            conditions.append(OfficialDocument.doc_type == doc_type)
        if status:
            conditions.append(OfficialDocument.status == status)
        if category:
            conditions.append(OfficialDocument.category == category)
        if project_id:
            conditions.append(OfficialDocument.contract_project_id == project_id)

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            search_conditions = [
                getattr(OfficialDocument, field).ilike(search_pattern)
                for field in self.SEARCH_FIELDS
                if hasattr(OfficialDocument, field)
            ]
            if search_conditions:
                conditions.append(or_(*search_conditions))

        # 使用基類的投影分頁方法
        return await self.get_paginated_projected(
            fields=self.LIST_PROJECTION_FIELDS,
            page=page,
            page_size=page_size,
            order_by=sort_by,
            order_desc=(sort_order.lower() == 'desc'),
            conditions=conditions if conditions else None
        )

    async def get_summary_list(
        self,
        limit: int = 100,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        取得公文摘要列表（最小投影）

        用於下拉選單、自動完成等需要快速載入的場景。
        僅載入 SUMMARY_PROJECTION_FIELDS 定義的欄位。

        Args:
            limit: 取得筆數上限
            doc_type: 公文類型篩選（可選）

        Returns:
            公文摘要字典列表

        Example:
            summaries = await doc_repo.get_summary_list(limit=50, doc_type='收文')
        """
        if doc_type:
            return await self.find_by_projected(
                fields=self.SUMMARY_PROJECTION_FIELDS,
                limit=limit,
                order_by='doc_date',
                order_desc=True,
                doc_type=doc_type
            )
        return await self.get_all_projected(
            fields=self.SUMMARY_PROJECTION_FIELDS,
            limit=limit,
            order_by='doc_date',
            order_desc=True
        )

    async def get_pending_documents_projected(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        取得待處理公文列表（投影查詢）

        使用部分索引 ix_documents_pending_by_date 優化查詢效能。

        Args:
            page: 頁碼
            page_size: 每頁筆數

        Returns:
            分頁結果字典
        """
        conditions = [OfficialDocument.status == '待處理']

        return await self.get_paginated_projected(
            fields=self.LIST_PROJECTION_FIELDS,
            page=page,
            page_size=page_size,
            order_by='doc_date',
            order_desc=True,
            conditions=conditions
        )

    async def search_documents_projected(
        self,
        search_term: str,
        page: int = 1,
        page_size: int = 20,
        doc_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        搜尋公文（投影查詢）

        Args:
            search_term: 搜尋關鍵字
            page: 頁碼
            page_size: 每頁筆數
            doc_type: 公文類型篩選

        Returns:
            分頁結果字典
        """
        if not search_term:
            return await self.get_list_projected(
                page=page,
                page_size=page_size,
                doc_type=doc_type
            )

        # 建構搜尋條件
        search_pattern = f"%{search_term}%"
        search_conditions = [
            getattr(OfficialDocument, field).ilike(search_pattern)
            for field in self.SEARCH_FIELDS
            if hasattr(OfficialDocument, field)
        ]

        conditions = []
        if search_conditions:
            conditions.append(or_(*search_conditions))
        if doc_type:
            conditions.append(OfficialDocument.doc_type == doc_type)

        return await self.get_paginated_projected(
            fields=self.LIST_PROJECTION_FIELDS,
            page=page,
            page_size=page_size,
            order_by='doc_date',
            order_desc=True,
            conditions=conditions if conditions else None
        )

    # =========================================================================
    # 批次查詢方法 (v2.0.0, A6 提取)
    # =========================================================================

    async def get_project_names_by_ids(
        self, project_ids: List[int]
    ) -> Dict[int, str]:
        """批次取得專案名稱 {project_id: project_name}"""
        if not project_ids:
            return {}
        query = select(ContractProject.id, ContractProject.project_name).where(
            ContractProject.id.in_(project_ids)
        )
        result = await self.db.execute(query)
        return {row.id: row.project_name for row in result.all()}

    async def get_attachment_counts_batch(
        self, doc_ids: List[int]
    ) -> Dict[int, int]:
        """批次取得附件數量 {document_id: count}"""
        if not doc_ids:
            return {}
        query = (
            select(
                DocumentAttachment.document_id,
                func.count(DocumentAttachment.id).label('count')
            )
            .where(DocumentAttachment.document_id.in_(doc_ids))
            .group_by(DocumentAttachment.document_id)
        )
        result = await self.db.execute(query)
        return {row.document_id: int(row.count) for row in result.all()}

    async def get_agency_names_by_ids(
        self, agency_ids: List[int]
    ) -> Dict[int, str]:
        """批次取得機關名稱 {agency_id: agency_name}"""
        if not agency_ids:
            return {}
        query = select(GovernmentAgency.id, GovernmentAgency.agency_name).where(
            GovernmentAgency.id.in_(list(agency_ids))
        )
        result = await self.db.execute(query)
        return {row.id: row.agency_name for row in result.all()}

    async def search_distinct_subjects(
        self, keyword: str, limit: int = 10
    ) -> List[str]:
        """搜尋公文主旨 (ILIKE 模糊, distinct, 截斷 100 字)"""
        result = await self.db.execute(
            select(OfficialDocument.subject)
            .where(OfficialDocument.subject.ilike(f"%{keyword}%"))
            .distinct()
            .limit(limit)
        )
        return [row[0] for row in result.all() if row[0]]

    async def search_distinct_doc_numbers(
        self, keyword: str, limit: int = 10
    ) -> List[str]:
        """搜尋公文字號 (ILIKE 模糊, distinct)"""
        result = await self.db.execute(
            select(OfficialDocument.doc_number)
            .where(OfficialDocument.doc_number.ilike(f"%{keyword}%"))
            .distinct()
            .limit(limit)
        )
        return [row[0] for row in result.all() if row[0]]

    async def get_recent_subjects(self, limit: int = 100) -> List[str]:
        """取得最近更新的公文主旨 (用於熱門搜尋)"""
        result = await self.db.execute(
            select(OfficialDocument.subject)
            .order_by(OfficialDocument.updated_at.desc())
            .limit(limit)
        )
        return [row[0] for row in result.all() if row[0]]

    async def get_max_serial_by_prefix(self, prefix: str) -> Optional[str]:
        """取得指定前綴的最大流水序號字串"""
        query = select(func.max(OfficialDocument.auto_serial)).where(
            OfficialDocument.auto_serial.like(f'{prefix}%')
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def build_doc_number_map(self) -> Dict[str, int]:
        """建立 {doc_number (stripped): doc_id} 映射"""
        query = select(OfficialDocument.id, OfficialDocument.doc_number).where(
            OfficialDocument.doc_number.isnot(None)
        )
        result = await self.db.execute(query)
        return {
            row.doc_number.strip(): row.id
            for row in result.all()
            if row.doc_number and row.doc_number.strip()
        }
