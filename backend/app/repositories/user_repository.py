"""
UserRepository - 使用者資料存取層

提供 User 模型的 CRUD 操作和常用查詢方法。

版本: 1.0.0
建立日期: 2026-02-06
"""

import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.repositories.base_repository import BaseRepository
from app.extended.models import User

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """
    使用者資料存取層

    提供使用者相關的資料庫操作，包含：
    - 基礎 CRUD（繼承自 BaseRepository）
    - 依 email/username 查詢
    - 活躍使用者列表
    - 使用者統計

    Example:
        repo = UserRepository(db)
        user = await repo.get_by_email("admin@example.com")
        active_users = await repo.get_active_users()
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """根據 email 取得使用者"""
        return await self.find_one_by(email=email)

    async def get_by_username(self, username: str) -> Optional[User]:
        """根據 username 取得使用者"""
        return await self.find_one_by(username=username)

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[User]:
        """
        取得活躍使用者列表

        Args:
            skip: 跳過筆數
            limit: 取得筆數
            search: 搜尋關鍵字（搜尋 username、display_name、email）

        Returns:
            活躍使用者列表
        """
        query = select(User).where(User.is_active == True)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(pattern),
                    User.display_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        query = query.order_by(User.username).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_count(self, search: Optional[str] = None) -> int:
        """取得活躍使用者總數"""
        query = select(func.count(User.id)).where(User.is_active == True)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(pattern),
                    User.display_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def check_username_exists(
        self, username: str, exclude_id: Optional[int] = None
    ) -> bool:
        """
        檢查 username 是否已存在

        Args:
            username: 使用者名稱
            exclude_id: 排除的使用者 ID（用於更新時排除自己）
        """
        query = select(func.count(User.id)).where(User.username == username)
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def check_email_exists(
        self, email: str, exclude_id: Optional[int] = None
    ) -> bool:
        """
        檢查 email 是否已存在

        Args:
            email: 電子郵件
            exclude_id: 排除的使用者 ID
        """
        query = select(func.count(User.id)).where(User.email == email)
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0
