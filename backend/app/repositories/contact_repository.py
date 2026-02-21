"""
ContactRepository - 專案機關承辦資料存取層

提供專案機關承辦（ProjectAgencyContact）相關的資料庫查詢操作，包含：
- 依專案查詢承辦人
- 依機關查詢承辦人
- 主要承辦人管理
- 進階篩選

版本: 1.0.0
建立日期: 2026-02-21
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, desc

from app.repositories.base_repository import BaseRepository
from app.extended.models import ProjectAgencyContact

logger = logging.getLogger(__name__)


class ContactRepository(BaseRepository[ProjectAgencyContact]):
    """
    專案機關承辦資料存取層

    繼承 BaseRepository 並擴展承辦人特定的查詢方法。

    Example:
        contact_repo = ContactRepository(db)

        # 依專案查詢
        contacts = await contact_repo.get_by_project_id(project_id=1)

        # 篩選
        contacts, total = await contact_repo.filter_contacts(
            project_id=1, keyword="王"
        )
    """

    # 搜尋欄位設定
    SEARCH_FIELDS = ['contact_name', 'department', 'email', 'phone']

    def __init__(self, db: AsyncSession):
        """
        初始化承辦人 Repository

        Args:
            db: AsyncSession 資料庫連線
        """
        super().__init__(db, ProjectAgencyContact)

    # =========================================================================
    # 依專案查詢
    # =========================================================================

    async def get_by_project_id(
        self,
        project_id: int,
    ) -> List[ProjectAgencyContact]:
        """
        取得專案的所有承辦人，主要承辦人排前面

        Args:
            project_id: 專案 ID

        Returns:
            承辦人列表（主要承辦人優先）
        """
        query = (
            select(ProjectAgencyContact)
            .where(ProjectAgencyContact.project_id == project_id)
            .order_by(
                ProjectAgencyContact.is_primary.desc(),
                ProjectAgencyContact.id
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_project_id_with_count(
        self,
        project_id: int,
    ) -> Dict[str, Any]:
        """
        取得專案的所有承辦人（含計數），供列表 API 使用

        Args:
            project_id: 專案 ID

        Returns:
            {"items": 承辦人列表, "total": 總數}
        """
        contacts = await self.get_by_project_id(project_id)
        return {
            "items": contacts,
            "total": len(contacts)
        }

    # =========================================================================
    # 主要承辦人管理
    # =========================================================================

    async def clear_primary_contact(
        self,
        project_id: int,
        exclude_id: Optional[int] = None
    ) -> None:
        """
        清除專案中其他主要承辦人標記

        Args:
            project_id: 專案 ID
            exclude_id: 排除的承辦人 ID（可選）
        """
        stmt = (
            update(ProjectAgencyContact)
            .where(
                ProjectAgencyContact.project_id == project_id,
                ProjectAgencyContact.is_primary == True  # noqa: E712
            )
            .values(is_primary=False)
        )

        if exclude_id:
            stmt = stmt.where(ProjectAgencyContact.id != exclude_id)

        await self.db.execute(stmt)

    async def get_primary_contact(
        self,
        project_id: int
    ) -> Optional[ProjectAgencyContact]:
        """
        取得專案的主要承辦人

        Args:
            project_id: 專案 ID

        Returns:
            主要承辦人，若無則返回 None
        """
        return await self.find_one_by(
            project_id=project_id,
            is_primary=True
        )

    # =========================================================================
    # 進階篩選
    # =========================================================================

    async def filter_contacts(
        self,
        project_id: Optional[int] = None,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ProjectAgencyContact], int]:
        """
        進階篩選承辦人

        Args:
            project_id: 專案 ID（可選）
            category: 類別篩選（機關/乾坤/廠商）
            keyword: 關鍵字搜尋
            page: 頁碼（從 1 開始）
            page_size: 每頁筆數

        Returns:
            (承辦人列表, 總數) 元組
        """
        conditions: List[Any] = []

        if project_id is not None:
            conditions.append(ProjectAgencyContact.project_id == project_id)

        if category:
            conditions.append(ProjectAgencyContact.category == category)

        if keyword:
            keyword_pattern = f"%{keyword}%"
            search_conditions = [
                ProjectAgencyContact.contact_name.ilike(keyword_pattern),
                ProjectAgencyContact.department.ilike(keyword_pattern),
                ProjectAgencyContact.email.ilike(keyword_pattern),
                ProjectAgencyContact.phone.ilike(keyword_pattern),
            ]
            conditions.append(or_(*search_conditions))

        query = select(ProjectAgencyContact)
        if conditions:
            query = query.where(and_(*conditions))

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分頁與排序
        offset = (page - 1) * page_size
        query = query.order_by(
            ProjectAgencyContact.is_primary.desc(),
            ProjectAgencyContact.id
        ).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        contacts = list(result.scalars().all())

        return contacts, total

    async def count_by_project(self, project_id: int) -> int:
        """
        取得專案的承辦人數量

        Args:
            project_id: 專案 ID

        Returns:
            承辦人數量
        """
        return await self.count_by(project_id=project_id)
