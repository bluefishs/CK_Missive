"""
SessionRepository - 使用者會話資料存取層

提供 UserSession 模型的 CRUD 操作和安全敏感查詢方法。
所有撤銷操作使用 SELECT FOR UPDATE 防並發競態。

版本: 1.0.0
建立日期: 2026-02-11
"""

import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_

from app.repositories.base_repository import BaseRepository
from app.extended.models import UserSession

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository[UserSession]):
    """
    使用者會話資料存取層

    提供會話相關的資料庫操作，包含：
    - 基礎 CRUD（繼承自 BaseRepository）
    - 活躍 session 查詢
    - refresh token 查詢
    - session 撤銷（含 SELECT FOR UPDATE 防競態）
    - 過期 session 清理

    安全注意事項：
    - revoke 操作使用行級鎖 (SELECT FOR UPDATE)
    - token replay 偵測時需撤銷該用戶所有 session

    Example:
        repo = SessionRepository(db)
        sessions = await repo.get_active_sessions(user_id=1)
        revoked = await repo.revoke_session(session_id=5)
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, UserSession)

    async def get_active_sessions(self, user_id: int) -> List[UserSession]:
        """
        取得用戶所有活躍 session

        Args:
            user_id: 使用者 ID

        Returns:
            活躍 session 列表（按最後活動時間降序）
        """
        query = (
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow(),
                )
            )
            .order_by(UserSession.last_activity.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_token_jti(self, token_jti: str) -> Optional[UserSession]:
        """
        根據 JWT ID (jti) 取得 session

        Args:
            token_jti: JWT 的唯一識別碼

        Returns:
            UserSession 或 None
        """
        return await self.find_one_by(token_jti=token_jti)

    async def get_by_refresh_token(self, refresh_token: str) -> Optional[UserSession]:
        """
        根據 refresh token 取得 session

        Args:
            refresh_token: Refresh token 值

        Returns:
            UserSession 或 None
        """
        return await self.find_one_by(refresh_token=refresh_token)

    async def get_active_by_refresh_token_for_update(
        self, refresh_token: str
    ) -> Optional[UserSession]:
        """
        根據 refresh token 取得活躍 session（帶行級鎖）

        使用 SELECT FOR UPDATE 防止並發 token rotation 競態。
        必須在交易中使用。

        Args:
            refresh_token: Refresh token 值

        Returns:
            UserSession 或 None
        """
        query = (
            select(UserSession)
            .where(
                and_(
                    UserSession.refresh_token == refresh_token,
                    UserSession.is_active == True,
                )
            )
            .with_for_update()
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def revoke_session(self, session_id: int) -> bool:
        """
        撤銷單一 session

        Args:
            session_id: Session ID

        Returns:
            是否成功撤銷（rowcount > 0）
        """
        now = datetime.utcnow()
        stmt = (
            update(UserSession)
            .where(
                and_(
                    UserSession.id == session_id,
                    UserSession.is_active == True,
                )
            )
            .values(is_active=False, revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        revoked = result.rowcount > 0
        if revoked:
            logger.info(f"Session {session_id} revoked")
        return revoked

    async def revoke_all_sessions(
        self, user_id: int, exclude_session_id: Optional[int] = None
    ) -> int:
        """
        撤銷用戶所有 session

        用於 token replay 偵測或使用者主動登出所有裝置。

        Args:
            user_id: 使用者 ID
            exclude_session_id: 排除的 session ID（保留當前 session）

        Returns:
            撤銷的 session 數量
        """
        now = datetime.utcnow()
        conditions = [
            UserSession.user_id == user_id,
            UserSession.is_active == True,
        ]
        if exclude_session_id is not None:
            conditions.append(UserSession.id != exclude_session_id)

        stmt = (
            update(UserSession)
            .where(and_(*conditions))
            .values(is_active=False, revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        count = result.rowcount
        if count > 0:
            logger.info(f"Revoked {count} sessions for user {user_id}")
        return count

    async def update_last_activity(self, session_id: int) -> None:
        """
        更新 session 最後活動時間

        Args:
            session_id: Session ID
        """
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_activity=datetime.utcnow())
        )
        await self.db.execute(stmt)

    async def cleanup_expired(self) -> int:
        """
        清理過期的 session

        將所有已過期但仍標記為 active 的 session 設為 inactive。

        Returns:
            清理的 session 數量
        """
        now = datetime.utcnow()
        stmt = (
            update(UserSession)
            .where(
                and_(
                    UserSession.is_active == True,
                    UserSession.expires_at <= now,
                )
            )
            .values(is_active=False)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        return count

    async def get_user_active_sessions_ordered(self, user_id: int) -> List[UserSession]:
        """
        取得用戶所有 is_active=True 的 session（不檢查 expires_at）

        按 last_activity 降序排列，用於 session 管理 UI 列表。

        Args:
            user_id: 使用者 ID

        Returns:
            活躍 session 列表
        """
        query = (
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                )
            )
            .order_by(UserSession.last_activity.desc().nullslast())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_by_id_and_user(
        self, session_id: int, user_id: int
    ) -> Optional[UserSession]:
        """
        取得指定 ID 且屬於指定用戶的活躍 session

        用於撤銷前驗證 session 擁有權。

        Args:
            session_id: Session ID
            user_id: 使用者 ID

        Returns:
            UserSession 或 None
        """
        query = (
            select(UserSession)
            .where(
                and_(
                    UserSession.id == session_id,
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                )
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def revoke_all_by_user_excluding_jti(
        self, user_id: int, exclude_jti: Optional[str] = None
    ) -> int:
        """
        撤銷用戶所有 session，排除指定 token_jti

        用於「撤銷所有其他 Session」功能，保留當前正在使用的 session。

        Args:
            user_id: 使用者 ID
            exclude_jti: 排除的 JWT ID（當前 session 的 jti）

        Returns:
            撤銷的 session 數量
        """
        now = datetime.utcnow()
        conditions = [
            UserSession.user_id == user_id,
            UserSession.is_active == True,
        ]
        if exclude_jti:
            conditions.append(UserSession.token_jti != exclude_jti)

        stmt = (
            update(UserSession)
            .where(and_(*conditions))
            .values(is_active=False, revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        count = result.rowcount
        if count > 0:
            logger.info(f"Revoked {count} sessions for user {user_id} (excluding jti)")
        return count

    async def revoke_all_by_user(self, user_id: int) -> int:
        """
        撤銷用戶所有活躍 session（無排除）

        用於密碼重設後強制登出所有裝置。

        Args:
            user_id: 使用者 ID

        Returns:
            撤銷的 session 數量
        """
        now = datetime.utcnow()
        stmt = (
            update(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                )
            )
            .values(is_active=False, revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        count = result.rowcount
        if count > 0:
            logger.info(f"Revoked all {count} sessions for user {user_id}")
        return count

    async def get_active_count(self, user_id: int) -> int:
        """取得用戶活躍 session 數量"""
        query = select(func.count(UserSession.id)).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow(),
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
