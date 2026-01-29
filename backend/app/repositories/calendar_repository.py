"""
CalendarRepository - 行事曆事件資料存取層

提供行事曆事件的 CRUD 操作和特定查詢方法。

@version 1.0.0
@date 2026-01-28
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload

from .base_repository import BaseRepository
from app.extended.models import DocumentCalendarEvent, EventReminder, User

logger = logging.getLogger(__name__)


class CalendarRepository(BaseRepository[DocumentCalendarEvent]):
    """
    行事曆事件資料存取層

    繼承 BaseRepository 並提供行事曆事件特定的查詢方法
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, DocumentCalendarEvent)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_with_reminders(
        self, event_id: int
    ) -> Optional[DocumentCalendarEvent]:
        """
        取得事件及其提醒

        Args:
            event_id: 事件 ID

        Returns:
            事件（含提醒）或 None
        """
        query = (
            select(DocumentCalendarEvent)
            .options(
                selectinload(DocumentCalendarEvent.reminders),
                selectinload(DocumentCalendarEvent.document),
                selectinload(DocumentCalendarEvent.assigned_user),
                selectinload(DocumentCalendarEvent.creator),
            )
            .where(DocumentCalendarEvent.id == event_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_document(
        self, document_id: int
    ) -> List[DocumentCalendarEvent]:
        """
        取得公文的所有事件

        Args:
            document_id: 公文 ID

        Returns:
            事件列表
        """
        query = (
            select(DocumentCalendarEvent)
            .options(selectinload(DocumentCalendarEvent.reminders))
            .where(DocumentCalendarEvent.document_id == document_id)
            .order_by(DocumentCalendarEvent.start_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_created: bool = True,
    ) -> List[DocumentCalendarEvent]:
        """
        取得使用者的事件

        Args:
            user_id: 使用者 ID
            start_date: 開始日期
            end_date: 結束日期
            include_created: 是否包含使用者建立的事件

        Returns:
            事件列表
        """
        conditions = []

        if include_created:
            conditions.append(
                or_(
                    DocumentCalendarEvent.assigned_user_id == user_id,
                    DocumentCalendarEvent.created_by == user_id,
                )
            )
        else:
            conditions.append(DocumentCalendarEvent.assigned_user_id == user_id)

        if start_date:
            conditions.append(DocumentCalendarEvent.start_date >= start_date)
        if end_date:
            conditions.append(DocumentCalendarEvent.start_date <= end_date)

        query = (
            select(DocumentCalendarEvent)
            .options(
                selectinload(DocumentCalendarEvent.reminders),
                selectinload(DocumentCalendarEvent.document),
            )
            .where(and_(*conditions))
            .order_by(DocumentCalendarEvent.start_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def filter_events(
        self,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[DocumentCalendarEvent], int]:
        """
        篩選事件列表

        Args:
            user_id: 使用者 ID
            document_id: 公文 ID
            event_type: 事件類型
            status: 狀態
            start_date: 開始日期
            end_date: 結束日期
            page: 頁碼
            limit: 每頁筆數

        Returns:
            (事件列表, 總筆數)
        """
        query = select(DocumentCalendarEvent).options(
            selectinload(DocumentCalendarEvent.reminders),
            selectinload(DocumentCalendarEvent.document),
        )

        conditions = []
        if user_id:
            conditions.append(
                or_(
                    DocumentCalendarEvent.assigned_user_id == user_id,
                    DocumentCalendarEvent.created_by == user_id,
                )
            )
        if document_id:
            conditions.append(DocumentCalendarEvent.document_id == document_id)
        if event_type:
            conditions.append(DocumentCalendarEvent.event_type == event_type)
        if status:
            conditions.append(DocumentCalendarEvent.status == status)
        if start_date:
            conditions.append(DocumentCalendarEvent.start_date >= start_date)
        if end_date:
            conditions.append(DocumentCalendarEvent.start_date <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分頁
        offset = (page - 1) * limit
        query = query.order_by(DocumentCalendarEvent.start_date.asc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    # =========================================================================
    # Google 同步相關
    # =========================================================================

    async def get_pending_sync_events(
        self, limit: int = 100
    ) -> List[DocumentCalendarEvent]:
        """
        取得待同步的事件 (含 reminders 關聯，供 Google Calendar 同步使用)

        Args:
            limit: 筆數上限

        Returns:
            待同步事件列表
        """
        query = (
            select(DocumentCalendarEvent)
            .options(
                selectinload(DocumentCalendarEvent.document),
                selectinload(DocumentCalendarEvent.reminders),  # 需要載入以計算提醒時間
            )
            .where(
                or_(
                    DocumentCalendarEvent.google_sync_status == 'pending',
                    DocumentCalendarEvent.google_sync_status.is_(None),
                )
            )
            .order_by(DocumentCalendarEvent.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_synced_events(self) -> List[DocumentCalendarEvent]:
        """
        取得已同步的事件

        Returns:
            已同步事件列表
        """
        return await self.find_by(google_sync_status='synced')

    async def get_failed_sync_events(self) -> List[DocumentCalendarEvent]:
        """
        取得同步失敗的事件

        Returns:
            同步失敗事件列表
        """
        return await self.find_by(google_sync_status='failed')

    async def mark_synced(
        self, event_id: int, google_event_id: str
    ) -> Optional[DocumentCalendarEvent]:
        """
        標記事件為已同步

        Args:
            event_id: 事件 ID
            google_event_id: Google Calendar 事件 ID

        Returns:
            更新後的事件或 None
        """
        return await self.update(event_id, {
            'google_event_id': google_event_id,
            'google_sync_status': 'synced',
        })

    async def mark_sync_failed(
        self, event_id: int, error: Optional[str] = None
    ) -> Optional[DocumentCalendarEvent]:
        """
        標記事件同步失敗

        Args:
            event_id: 事件 ID
            error: 錯誤訊息

        Returns:
            更新後的事件或 None
        """
        return await self.update(event_id, {
            'google_sync_status': 'failed',
        })

    # =========================================================================
    # 衝突檢測
    # =========================================================================

    async def get_conflicting_events(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> List[DocumentCalendarEvent]:
        """
        取得時間衝突的事件

        Args:
            start_time: 開始時間
            end_time: 結束時間
            exclude_id: 排除的事件 ID
            user_id: 使用者 ID（可選）

        Returns:
            衝突事件列表
        """
        conditions = [
            # 檢查時間重疊
            and_(
                DocumentCalendarEvent.start_date < end_time,
                DocumentCalendarEvent.end_date > start_time,
            )
        ]

        if exclude_id:
            conditions.append(DocumentCalendarEvent.id != exclude_id)

        if user_id:
            conditions.append(
                or_(
                    DocumentCalendarEvent.assigned_user_id == user_id,
                    DocumentCalendarEvent.created_by == user_id,
                )
            )

        query = (
            select(DocumentCalendarEvent)
            .where(and_(*conditions))
            .order_by(DocumentCalendarEvent.start_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def check_document_has_events(self, document_id: int) -> bool:
        """
        檢查公文是否有事件

        Args:
            document_id: 公文 ID

        Returns:
            是否有事件
        """
        return await self.exists_by(document_id=document_id)

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def count_by_status(self, user_id: Optional[int] = None) -> Dict[str, int]:
        """
        依狀態統計事件數量

        Args:
            user_id: 使用者 ID（可選）

        Returns:
            {狀態: 數量} 字典
        """
        query = select(
            DocumentCalendarEvent.status,
            func.count(DocumentCalendarEvent.id),
        ).group_by(DocumentCalendarEvent.status)

        if user_id:
            query = query.where(
                or_(
                    DocumentCalendarEvent.assigned_user_id == user_id,
                    DocumentCalendarEvent.created_by == user_id,
                )
            )

        result = await self.db.execute(query)
        return {row[0] or 'unknown': row[1] for row in result.fetchall()}

    async def count_upcoming(
        self, user_id: Optional[int] = None, days: int = 7
    ) -> int:
        """
        統計即將到來的事件數量

        Args:
            user_id: 使用者 ID（可選）
            days: 天數

        Returns:
            事件數量
        """
        now = datetime.now()
        end_date = now + timedelta(days=days)

        conditions = [
            DocumentCalendarEvent.start_date >= now,
            DocumentCalendarEvent.start_date <= end_date,
            DocumentCalendarEvent.status != 'completed',
        ]

        if user_id:
            conditions.append(
                or_(
                    DocumentCalendarEvent.assigned_user_id == user_id,
                    DocumentCalendarEvent.created_by == user_id,
                )
            )

        query = select(func.count(DocumentCalendarEvent.id)).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def count_overdue(self, user_id: Optional[int] = None) -> int:
        """
        統計逾期事件數量

        Args:
            user_id: 使用者 ID（可選）

        Returns:
            逾期事件數量
        """
        now = datetime.now()

        conditions = [
            DocumentCalendarEvent.end_date < now,
            DocumentCalendarEvent.status != 'completed',
        ]

        if user_id:
            conditions.append(
                or_(
                    DocumentCalendarEvent.assigned_user_id == user_id,
                    DocumentCalendarEvent.created_by == user_id,
                )
            )

        query = select(func.count(DocumentCalendarEvent.id)).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_statistics(
        self, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        取得行事曆統計資料

        Args:
            user_id: 使用者 ID（可選）

        Returns:
            統計資料字典
        """
        by_status = await self.count_by_status(user_id)
        upcoming = await self.count_upcoming(user_id)
        overdue = await self.count_overdue(user_id)

        total = sum(by_status.values())

        return {
            'total': total,
            'by_status': by_status,
            'upcoming_7_days': upcoming,
            'overdue': overdue,
        }
