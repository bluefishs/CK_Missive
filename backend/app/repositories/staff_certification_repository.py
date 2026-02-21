"""
StaffCertificationRepository - 證照資料存取層

提供承辦同仁證照相關的資料庫查詢操作，包含：
- 依使用者查詢證照
- 即將到期證照查詢
- 進階篩選（類型、狀態、關鍵字）
- 統計方法

版本: 1.0.0
建立日期: 2026-02-21
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc

from app.repositories.base_repository import BaseRepository
from app.extended.models import StaffCertification

logger = logging.getLogger(__name__)


class StaffCertificationRepository(BaseRepository[StaffCertification]):
    """
    證照資料存取層

    繼承 BaseRepository 並擴展證照特定的查詢方法。

    Example:
        cert_repo = StaffCertificationRepository(db)

        # 基本查詢
        cert = await cert_repo.get_by_id(1)

        # 依使用者查詢
        certs = await cert_repo.get_by_user_id(user_id=5)

        # 即將到期
        expiring = await cert_repo.get_expiring_soon(days=30)
    """

    # 搜尋欄位設定
    SEARCH_FIELDS = ['cert_name', 'issuing_authority', 'cert_number']

    def __init__(self, db: AsyncSession):
        """
        初始化證照 Repository

        Args:
            db: AsyncSession 資料庫連線
        """
        super().__init__(db, StaffCertification)

    # =========================================================================
    # 依使用者查詢
    # =========================================================================

    async def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[StaffCertification]:
        """
        取得指定使用者的所有證照

        Args:
            user_id: 使用者 ID
            skip: 跳過筆數
            limit: 取得筆數上限

        Returns:
            證照列表
        """
        query = (
            select(StaffCertification)
            .where(StaffCertification.user_id == user_id)
            .order_by(desc(StaffCertification.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 即將到期查詢
    # =========================================================================

    async def get_expiring_soon(
        self,
        days: int = 30,
        user_id: Optional[int] = None
    ) -> List[StaffCertification]:
        """
        取得即將到期的證照

        Args:
            days: 到期天數閾值（預設 30 天內）
            user_id: 若指定則只查詢特定使用者

        Returns:
            即將到期的證照列表
        """
        threshold_date = date.today() + timedelta(days=days)

        conditions = [
            StaffCertification.expiry_date.isnot(None),
            StaffCertification.expiry_date <= threshold_date,
            StaffCertification.expiry_date >= date.today(),
            StaffCertification.status == '有效',
        ]

        if user_id is not None:
            conditions.append(StaffCertification.user_id == user_id)

        query = (
            select(StaffCertification)
            .where(and_(*conditions))
            .order_by(StaffCertification.expiry_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # 進階篩選
    # =========================================================================

    async def filter_certifications(
        self,
        user_id: int,
        cert_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[StaffCertification], int]:
        """
        進階篩選使用者證照

        Args:
            user_id: 使用者 ID
            cert_type: 證照類型篩選
            status: 狀態篩選
            keyword: 關鍵字搜尋（搜尋名稱、核發機關、編號）
            page: 頁碼（從 1 開始）
            page_size: 每頁筆數

        Returns:
            (證照列表, 總數) 元組
        """
        query = select(StaffCertification).where(
            StaffCertification.user_id == user_id
        )
        conditions = [StaffCertification.user_id == user_id]

        # 類型篩選
        if cert_type:
            conditions.append(StaffCertification.cert_type == cert_type)

        # 狀態篩選
        if status:
            conditions.append(StaffCertification.status == status)

        # 關鍵字搜尋
        if keyword:
            keyword_pattern = f"%{keyword}%"
            search_conditions = [
                StaffCertification.cert_name.ilike(keyword_pattern),
                StaffCertification.issuing_authority.ilike(keyword_pattern),
                StaffCertification.cert_number.ilike(keyword_pattern),
            ]
            conditions.append(or_(*search_conditions))

        query = select(StaffCertification).where(and_(*conditions))

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分頁與排序
        offset = (page - 1) * page_size
        query = query.order_by(desc(StaffCertification.created_at)).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        certifications = list(result.scalars().all())

        return certifications, total

    # =========================================================================
    # 統計方法
    # =========================================================================

    async def get_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        取得使用者證照統計

        Args:
            user_id: 使用者 ID

        Returns:
            統計資料字典：{by_type, by_status, total}
        """
        # 依類型統計
        type_query = (
            select(
                StaffCertification.cert_type,
                func.count(StaffCertification.id).label('count')
            )
            .where(StaffCertification.user_id == user_id)
            .group_by(StaffCertification.cert_type)
        )
        type_result = await self.db.execute(type_query)
        type_stats = type_result.all()

        # 依狀態統計
        status_query = (
            select(
                StaffCertification.status,
                func.count(StaffCertification.id).label('count')
            )
            .where(StaffCertification.user_id == user_id)
            .group_by(StaffCertification.status)
        )
        status_result = await self.db.execute(status_query)
        status_stats = status_result.all()

        return {
            "by_type": {row.cert_type: row.count for row in type_stats},
            "by_status": {row.status: row.count for row in status_stats},
            "total": sum(row.count for row in type_stats),
        }
