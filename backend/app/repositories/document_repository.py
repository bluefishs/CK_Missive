"""
DocumentRepository - 公文資料存取層

提供公文相關的資料庫查詢操作，包含：
- 公文特定查詢方法
- 附件關聯查詢
- 統計方法
- 進階篩選

版本: 1.0.0
建立日期: 2026-01-26
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
    """

    # 搜尋欄位設定
    SEARCH_FIELDS = ['subject', 'doc_number', 'sender', 'receiver', 'ck_note']

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
    # 統計方法
    # =========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得公文統計資料

        Returns:
            統計資料字典，包含：
            - total: 總數
            - by_type: 依類型統計
            - by_status: 依狀態統計
            - by_month: 依月份統計（當年度）
        """
        # 總數
        total = await self.count()

        # 依類型統計
        type_stats = await self._get_grouped_count('doc_type')

        # 依狀態統計
        status_stats = await self._get_grouped_count('status')

        # 當年度月份統計
        current_year = date.today().year
        month_stats = await self._get_monthly_count(current_year)

        return {
            "total": total,
            "by_type": type_stats,
            "by_status": status_stats,
            "by_month": month_stats,
            "year": current_year,
        }

    async def get_type_statistics(self) -> Dict[str, int]:
        """
        取得依類型統計

        Returns:
            {類型: 數量} 字典
        """
        return await self._get_grouped_count('doc_type')

    async def get_status_statistics(self) -> Dict[str, int]:
        """
        取得依狀態統計

        Returns:
            {狀態: 數量} 字典
        """
        return await self._get_grouped_count('status')

    async def get_yearly_statistics(self, year: int) -> Dict[str, Any]:
        """
        取得年度統計

        Args:
            year: 年度

        Returns:
            年度統計資料
        """
        # 該年度總數
        query = select(func.count(OfficialDocument.id)).where(
            or_(
                extract('year', OfficialDocument.doc_date) == year,
                extract('year', OfficialDocument.receive_date) == year
            )
        )
        total = (await self.db.execute(query)).scalar() or 0

        # 月份統計
        month_stats = await self._get_monthly_count(year)

        # 類型統計（該年度）
        type_stats = await self._get_grouped_count_with_year('doc_type', year)

        return {
            "year": year,
            "total": total,
            "by_month": month_stats,
            "by_type": type_stats,
        }

    async def get_pending_count(self) -> int:
        """
        取得待處理公文數量

        Returns:
            待處理公文數量
        """
        return await self.count_by(status='待處理')

    async def get_unlinked_count(self) -> int:
        """
        取得未關聯專案的公文數量

        Returns:
            未關聯專案的公文數量
        """
        query = select(func.count(OfficialDocument.id)).where(
            OfficialDocument.contract_project_id.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_grouped_count(self, field_name: str) -> Dict[str, int]:
        """
        取得依欄位分組的計數

        Args:
            field_name: 欄位名稱

        Returns:
            {欄位值: 數量} 字典
        """
        field = getattr(OfficialDocument, field_name)
        query = (
            select(field, func.count(OfficialDocument.id))
            .group_by(field)
        )
        result = await self.db.execute(query)

        stats = {}
        for value, count in result.fetchall():
            key = value if value else '(未設定)'
            stats[key] = count
        return stats

    async def _get_grouped_count_with_year(
        self,
        field_name: str,
        year: int
    ) -> Dict[str, int]:
        """
        取得指定年度依欄位分組的計數

        Args:
            field_name: 欄位名稱
            year: 年度

        Returns:
            {欄位值: 數量} 字典
        """
        field = getattr(OfficialDocument, field_name)
        query = (
            select(field, func.count(OfficialDocument.id))
            .where(
                or_(
                    extract('year', OfficialDocument.doc_date) == year,
                    extract('year', OfficialDocument.receive_date) == year
                )
            )
            .group_by(field)
        )
        result = await self.db.execute(query)

        stats = {}
        for value, count in result.fetchall():
            key = value if value else '(未設定)'
            stats[key] = count
        return stats

    async def _get_monthly_count(self, year: int) -> Dict[int, int]:
        """
        取得指定年度的月份統計

        Args:
            year: 年度

        Returns:
            {月份: 數量} 字典
        """
        query = (
            select(
                extract('month', OfficialDocument.doc_date).label('month'),
                func.count(OfficialDocument.id)
            )
            .where(extract('year', OfficialDocument.doc_date) == year)
            .group_by(extract('month', OfficialDocument.doc_date))
        )
        result = await self.db.execute(query)

        # 初始化所有月份為 0
        stats = {i: 0 for i in range(1, 13)}
        for month, count in result.fetchall():
            if month:
                stats[int(month)] = count
        return stats

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
