# -*- coding: utf-8 -*-
"""
Row-Level Security (RLS) 過濾器

提供統一的行級別權限過濾邏輯，確保所有服務使用相同的權限檢查機制。

使用範例：
    from app.core.rls_filter import RLSFilter

    # 取得使用者可存取的專案 ID 子查詢
    project_ids_query = RLSFilter.get_user_accessible_project_ids(user_id)

    # 檢查使用者是否有權限存取特定專案
    has_access = await RLSFilter.check_user_project_access(db, user_id, project_id)

    # 套用公文查詢的 RLS 過濾
    query = RLSFilter.apply_document_rls(query, Document, user_id, is_admin)
"""
import logging
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import select, and_, or_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

if TYPE_CHECKING:
    from app.extended.models import User

logger = logging.getLogger(__name__)


class RLSFilter:
    """
    Row-Level Security 過濾器

    集中管理所有 RLS 相關的查詢邏輯，確保一致性。
    """

    # 有效的專案狀態（允許存取的狀態）
    ACTIVE_ASSIGNMENT_STATUSES = ['active', 'Active', None]

    @classmethod
    def get_user_accessible_project_ids(cls, user_id: int) -> Select:
        """
        取得使用者可存取的專案 ID 子查詢

        用於建構查詢條件，過濾使用者有權限存取的專案。

        Args:
            user_id: 使用者 ID

        Returns:
            可用於 .in_() 的子查詢
        """
        from app.extended.models import project_user_assignment

        return select(
            project_user_assignment.c.project_id
        ).where(
            and_(
                project_user_assignment.c.user_id == user_id,
                project_user_assignment.c.status.in_(cls.ACTIVE_ASSIGNMENT_STATUSES)
            )
        )

    @classmethod
    async def check_user_project_access(
        cls,
        db: AsyncSession,
        user_id: int,
        project_id: int
    ) -> bool:
        """
        檢查使用者是否有權限存取特定專案

        Args:
            db: 資料庫 session
            user_id: 使用者 ID
            project_id: 專案 ID

        Returns:
            True 如果有權限，否則 False
        """
        from app.extended.models import project_user_assignment

        result = await db.execute(
            select(exists().where(
                and_(
                    project_user_assignment.c.project_id == project_id,
                    project_user_assignment.c.user_id == user_id,
                    project_user_assignment.c.status.in_(cls.ACTIVE_ASSIGNMENT_STATUSES)
                )
            ))
        )
        return result.scalar()

    @classmethod
    def apply_document_rls(
        cls,
        query: Select,
        document_model,
        user_id: int,
        is_admin: bool = False,
        is_superuser: bool = False
    ) -> Select:
        """
        套用公文查詢的 RLS 過濾

        權限規則：
        - superuser/admin: 可查看所有公文
        - 一般使用者: 只能查看關聯專案的公文，或無專案關聯的公文

        Args:
            query: 原始查詢
            document_model: 公文模型類別
            user_id: 使用者 ID
            is_admin: 是否為管理員
            is_superuser: 是否為超級使用者

        Returns:
            套用 RLS 後的查詢
        """
        if is_admin or is_superuser:
            logger.debug(f"[RLS] 管理員 {user_id} 執行公文查詢（不套用行級別過濾）")
            return query

        logger.info(f"[RLS] 使用者 {user_id} 執行公文查詢（非管理員，套用行級別過濾）")

        # 取得使用者關聯的專案 ID 子查詢
        user_project_ids = cls.get_user_accessible_project_ids(user_id)

        # 公文過濾邏輯：
        # 1. 無專案關聯的公文（公開公文）
        # 2. 使用者有關聯的專案的公文
        return query.where(
            or_(
                document_model.contract_project_id.is_(None),  # 無專案關聯
                document_model.contract_project_id.in_(user_project_ids)  # 有關聯的專案
            )
        )

    @classmethod
    def apply_project_rls(
        cls,
        query: Select,
        project_model,
        user_id: int,
        is_admin: bool = False,
        is_superuser: bool = False
    ) -> Select:
        """
        套用專案查詢的 RLS 過濾

        權限規則：
        - superuser/admin: 可查看所有專案
        - 一般使用者: 只能查看自己關聯的專案

        Args:
            query: 原始查詢
            project_model: 專案模型類別
            user_id: 使用者 ID
            is_admin: 是否為管理員
            is_superuser: 是否為超級使用者

        Returns:
            套用 RLS 後的查詢
        """
        from app.extended.models import project_user_assignment

        if is_admin or is_superuser:
            logger.debug(f"[RLS] 管理員 {user_id} 執行專案查詢（不套用行級別過濾）")
            return query

        logger.info(f"[RLS] 使用者 {user_id} 執行專案查詢（非管理員，套用行級別過濾）")

        # 使用 exists 子查詢檢查關聯
        return query.where(
            exists().where(
                and_(
                    project_user_assignment.c.project_id == project_model.id,
                    project_user_assignment.c.user_id == user_id,
                    project_user_assignment.c.status.in_(cls.ACTIVE_ASSIGNMENT_STATUSES)
                )
            )
        )

    @classmethod
    def is_user_admin(cls, user: Optional["User"]) -> bool:
        """
        檢查使用者是否為管理員

        Args:
            user: 使用者物件

        Returns:
            True 如果是管理員或超級使用者
        """
        if user is None:
            return False
        is_admin = getattr(user, 'is_admin', False)
        is_superuser = getattr(user, 'is_superuser', False)
        return is_admin or is_superuser

    @classmethod
    def get_user_rls_flags(cls, user: Optional["User"]) -> tuple:
        """
        取得使用者的 RLS 標誌

        Args:
            user: 使用者物件

        Returns:
            (user_id, is_admin, is_superuser) 元組
        """
        if user is None:
            return (None, False, False)

        user_id = getattr(user, 'id', None)
        is_admin = getattr(user, 'is_admin', False)
        is_superuser = getattr(user, 'is_superuser', False)

        return (user_id, is_admin, is_superuser)
