"""
UserRepository - 使用者資料存取層

提供 User 模型的 CRUD 操作和常用查詢方法。

版本: 3.0.0
建立日期: 2026-02-06
更新日期: 2026-02-24
更新內容: 新增 create_user(), soft_delete(), get_sessions(), revoke_session()
"""

import logging
from typing import Optional, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update

from app.repositories.base_repository import BaseRepository
from app.extended.models import User, UserSession

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

    async def get_by_email_verification_token(self, token_hash: str) -> Optional[User]:
        """根據 email 驗證 token hash 取得使用者"""
        return await self.find_one_by(email_verification_token=token_hash)

    async def get_by_password_reset_token(
        self, token_hash: str, active_only: bool = True
    ) -> Optional[User]:
        """
        根據密碼重設 token hash 取得使用者

        Args:
            token_hash: SHA-256 token hash
            active_only: 是否僅查詢活躍使用者

        Returns:
            User 或 None
        """
        conditions = [User.password_reset_token == token_hash]
        if active_only:
            conditions.append(User.is_active == True)

        query = select(User).where(*conditions)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: int) -> Optional[User]:
        """
        根據 ID 取得活躍使用者

        Args:
            user_id: 使用者 ID

        Returns:
            活躍使用者或 None
        """
        query = select(User).where(User.id == user_id, User.is_active == True)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_fields(self, user_id: int, **kwargs) -> bool:
        """
        更新使用者指定欄位（使用 bulk update，不載入完整物件）

        適用於只需更新少量欄位且不需要回傳完整物件的場景。

        Args:
            user_id: 使用者 ID
            **kwargs: 要更新的欄位與值

        Returns:
            是否成功更新（rowcount > 0）
        """
        if not kwargs:
            return False
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**kwargs)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def update_and_refresh(self, user_id: int, **kwargs) -> Optional[User]:
        """
        更新使用者欄位並回傳更新後的完整物件。

        Args:
            user_id: 使用者 ID
            **kwargs: 要更新的欄位與值

        Returns:
            更新後的 User，或 None（使用者不存在）
        """
        if not kwargs:
            return await self.get_by_id(user_id)
        stmt = update(User).where(User.id == user_id).values(**kwargs)
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            return None
        await self.db.commit()
        user = await self.get_by_id(user_id)
        if user:
            await self.db.refresh(user)
        return user

    async def create_user(self, user: User) -> User:
        """建立新使用者並回傳"""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def soft_delete(self, user_id: int) -> bool:
        """軟刪除使用者（設為 is_active=False）"""
        return await self.update_fields(user_id, is_active=False)

    async def get_user_sessions(
        self, user_id: int
    ) -> List[UserSession]:
        """取得使用者的所有會話"""
        result = await self.db.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_session_by_id(self, session_id: int) -> Optional[UserSession]:
        """根據 ID 取得會話"""
        result = await self.db.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        return result.scalar_one_or_none()

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
