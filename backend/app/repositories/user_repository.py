"""
UserRepository - 使用者資料存取層

提供 User 模型的 CRUD 操作和常用查詢方法。

版本: 2.0.0
建立日期: 2026-02-06
更新日期: 2026-02-06
更新內容: 新增 get_users_filtered() 方法，支援篩選、搜尋、排序、分頁
"""

import logging
from typing import Optional, List, Tuple

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
            search: 搜尋關鍵字（搜尋 username、full_name、email）

        Returns:
            活躍使用者列表
        """
        query = select(User).where(User.is_active == True)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(pattern),
                    User.full_name.ilike(pattern),
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
                    User.full_name.ilike(pattern),
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

    async def get_users_filtered(
        self,
        *,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        department: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "id",
        sort_order: str = "asc",
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[User], int]:
        """
        篩選、搜尋、排序、分頁查詢使用者列表

        取代 users.py 端點中的直接 ORM 查詢，將資料存取邏輯
        集中於 Repository 層。

        Args:
            role: 角色篩選（精確匹配）
            is_active: 啟用狀態篩選
            department: 部門篩選（精確匹配）
            search: 搜尋關鍵字（模糊匹配 username、email、full_name）
            sort_by: 排序欄位名稱（預設 "id"）
            sort_order: 排序方向，"asc" 或 "desc"（預設 "asc"）
            page: 頁碼，從 1 開始（預設 1）
            limit: 每頁筆數（預設 20）

        Returns:
            (users, total) 元組：使用者列表與符合條件的總筆數

        Example:
            repo = UserRepository(db)
            users, total = await repo.get_users_filtered(
                role="admin",
                search="john",
                sort_by="created_at",
                sort_order="desc",
                page=1,
                limit=20,
            )
        """
        # 建立基本查詢
        data_query = select(User)
        count_query = select(func.count()).select_from(User)

        # 篩選條件
        if role is not None:
            data_query = data_query.where(User.role == role)
            count_query = count_query.where(User.role == role)

        if is_active is not None:
            data_query = data_query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        if department is not None:
            data_query = data_query.where(User.department == department)
            count_query = count_query.where(User.department == department)

        # 模糊搜尋
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            )
            data_query = data_query.where(search_filter)
            count_query = count_query.where(search_filter)

        # 取得總數
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 排序
        sort_column = getattr(User, sort_by, User.id)
        if sort_order == "desc":
            sort_column = sort_column.desc()

        # 分頁
        skip = (page - 1) * limit
        data_query = data_query.order_by(sort_column).offset(skip).limit(limit)

        result = await self.db.execute(data_query)
        users = list(result.scalars().all())

        return users, total
