"""
NotificationRepository - 系統通知資料存取層

提供系統通知的 CRUD 操作和特定查詢方法。

@version 1.0.0
@date 2026-01-28
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete

from .base_repository import BaseRepository
from app.extended.models import SystemNotification

logger = logging.getLogger(__name__)


class NotificationRepository(BaseRepository[SystemNotification]):
    """
    系統通知資料存取層

    繼承 BaseRepository 並提供系統通知特定的查詢方法
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, SystemNotification)

    # =========================================================================
    # 查詢方法
    # =========================================================================

    async def get_by_user(
        self,
        user_id: int,
        is_read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SystemNotification], int]:
        """
        取得使用者的通知

        Args:
            user_id: 使用者 ID
            is_read: 是否已讀（None 表示全部）
            limit: 筆數上限
            offset: 跳過筆數

        Returns:
            (通知列表, 總筆數)
        """
        conditions = [
            or_(
                SystemNotification.user_id == user_id,
                SystemNotification.recipient_id == user_id,
            )
        ]

        if is_read is not None:
            conditions.append(SystemNotification.is_read == is_read)

        query = (
            select(SystemNotification)
            .where(and_(*conditions))
            .order_by(SystemNotification.created_at.desc())
        )

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分頁
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_unread(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SystemNotification], int]:
        """
        取得使用者未讀通知

        Args:
            user_id: 使用者 ID
            limit: 筆數上限
            offset: 跳過筆數

        Returns:
            (通知列表, 總筆數)
        """
        return await self.get_by_user(user_id, is_read=False, limit=limit, offset=offset)

    async def filter_notifications(
        self,
        user_id: int,
        is_read: Optional[bool] = None,
        severity: Optional[str] = None,
        notification_type: Optional[str] = None,
        source_table: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SystemNotification], int]:
        """
        篩選通知列表

        Args:
            user_id: 使用者 ID
            is_read: 是否已讀
            severity: 嚴重程度
            notification_type: 通知類型
            source_table: 來源表格
            limit: 筆數上限
            offset: 跳過筆數

        Returns:
            (通知列表, 總筆數)
        """
        conditions = [
            or_(
                SystemNotification.user_id == user_id,
                SystemNotification.recipient_id == user_id,
            )
        ]

        if is_read is not None:
            conditions.append(SystemNotification.is_read == is_read)
        if notification_type:
            conditions.append(SystemNotification.notification_type == notification_type)
        # severity 和 source_table 存在 data 欄位中（JSONB）
        # 如需支援需要特殊處理

        query = (
            select(SystemNotification)
            .where(and_(*conditions))
            .order_by(SystemNotification.created_at.desc())
        )

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分頁
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_type(
        self,
        user_id: int,
        notification_type: str,
    ) -> List[SystemNotification]:
        """
        依類型取得通知

        Args:
            user_id: 使用者 ID
            notification_type: 通知類型

        Returns:
            通知列表
        """
        query = (
            select(SystemNotification)
            .where(
                and_(
                    or_(
                        SystemNotification.user_id == user_id,
                        SystemNotification.recipient_id == user_id,
                    ),
                    SystemNotification.notification_type == notification_type,
                )
            )
            .order_by(SystemNotification.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 狀態更新
    # =========================================================================

    async def mark_read(self, notification_id: int) -> bool:
        """
        標記通知為已讀

        Args:
            notification_id: 通知 ID

        Returns:
            是否成功
        """
        result = await self.update(notification_id, {
            'is_read': True,
            'read_at': datetime.now(),
        })
        return result is not None

    async def mark_read_batch(self, notification_ids: List[int]) -> int:
        """
        批次標記通知為已讀

        Args:
            notification_ids: 通知 ID 列表

        Returns:
            更新的筆數
        """
        if not notification_ids:
            return 0

        stmt = (
            update(SystemNotification)
            .where(SystemNotification.id.in_(notification_ids))
            .values(is_read=True, read_at=datetime.now())
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def mark_all_read(self, user_id: int) -> int:
        """
        標記使用者所有通知為已讀

        Args:
            user_id: 使用者 ID

        Returns:
            更新的筆數
        """
        stmt = (
            update(SystemNotification)
            .where(
                and_(
                    or_(
                        SystemNotification.user_id == user_id,
                        SystemNotification.recipient_id == user_id,
                    ),
                    SystemNotification.is_read == False,
                )
            )
            .values(is_read=True, read_at=datetime.now())
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def get_unread_count(self, user_id: int) -> int:
        """
        取得使用者未讀通知數量

        Args:
            user_id: 使用者 ID

        Returns:
            未讀數量
        """
        query = select(func.count(SystemNotification.id)).where(
            and_(
                or_(
                    SystemNotification.user_id == user_id,
                    SystemNotification.recipient_id == user_id,
                ),
                SystemNotification.is_read == False,
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    # =========================================================================
    # 來源查詢
    # =========================================================================

    async def get_by_source(
        self,
        source_table: str,
        source_id: int,
    ) -> List[SystemNotification]:
        """
        依來源取得通知

        Args:
            source_table: 來源表格名稱
            source_id: 來源記錄 ID

        Returns:
            通知列表
        """
        # 從 data JSON 欄位查詢
        query = (
            select(SystemNotification)
            .where(
                and_(
                    SystemNotification.data['source_table'].astext == source_table,
                    SystemNotification.data['source_id'].astext == str(source_id),
                )
            )
            .order_by(SystemNotification.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 清理方法
    # =========================================================================

    async def delete_old(self, older_than_days: int) -> int:
        """
        刪除舊通知

        Args:
            older_than_days: 天數閾值

        Returns:
            刪除的筆數
        """
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        stmt = delete(SystemNotification).where(
            SystemNotification.created_at < cutoff_date
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def delete_read_older_than(
        self,
        days: int,
        user_id: Optional[int] = None,
    ) -> int:
        """
        刪除已讀的舊通知

        Args:
            days: 天數閾值
            user_id: 使用者 ID（可選，不指定則刪除所有使用者的）

        Returns:
            刪除的筆數
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        conditions = [
            SystemNotification.is_read == True,
            SystemNotification.created_at < cutoff_date,
        ]

        if user_id:
            conditions.append(
                or_(
                    SystemNotification.user_id == user_id,
                    SystemNotification.recipient_id == user_id,
                )
            )

        stmt = delete(SystemNotification).where(and_(*conditions))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        取得使用者通知統計

        Args:
            user_id: 使用者 ID

        Returns:
            統計資料字典
        """
        # 總數
        total, _ = await self.get_by_user(user_id, limit=1)
        total_count = _

        # 未讀數
        unread_count = await self.get_unread_count(user_id)

        # 依類型統計
        type_query = (
            select(
                SystemNotification.notification_type,
                func.count(SystemNotification.id),
            )
            .where(
                or_(
                    SystemNotification.user_id == user_id,
                    SystemNotification.recipient_id == user_id,
                )
            )
            .group_by(SystemNotification.notification_type)
        )
        result = await self.db.execute(type_query)
        by_type = {row[0] or 'unknown': row[1] for row in result.fetchall()}

        # 今日通知數
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_query = select(func.count(SystemNotification.id)).where(
            and_(
                or_(
                    SystemNotification.user_id == user_id,
                    SystemNotification.recipient_id == user_id,
                ),
                SystemNotification.created_at >= today_start,
            )
        )
        today_result = await self.db.execute(today_query)
        today_count = today_result.scalar() or 0

        return {
            'total': total_count,
            'unread': unread_count,
            'read': total_count - unread_count,
            'by_type': by_type,
            'today': today_count,
        }
