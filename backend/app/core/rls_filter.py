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
from sqlalchemy import select, and_, or_, exists, func
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
    def get_alias_group_subquery(cls, user_id: int) -> Select:
        """
        取得使用者所屬 alias group 的所有 user_id 子查詢（TaskB, ADR-0025 配套）。

        邏輯：
            root_id = COALESCE(user.canonical_user_id, user.id)
                — 若 user 是 canonical：root = user.id
                — 若 user 是 alias：root = user.canonical_user_id

            alias group = { u | u.id == root_id OR u.canonical_user_id == root_id }
                — 包含 canonical 自己 + 所有指向 canonical 的 alias

        Args:
            user_id: 任一個 alias group 內的 user id（canonical 或 alias 都可）

        Returns:
            可用於 .in_() 的子查詢，回傳整組等價 user_id

        Why:
            未合併的同人多帳號（如李昭德 hotmail id=11 / gmail id=19）登入任一帳號，
            RLS 應展開到整組以共享 project_user_assignments / dispatch / 等 FK 關聯。
            合併後（canonical_user_id 已設）也維持同樣行為，無需改動 caller。

        Note:
            user_id 不存在時，退化為 {user_id} 自己（外部 IN 條件無 row 命中即拒絕，安全）。
        """
        from app.extended.models import User

        # 子查詢 1：解析該 user 的 root_id（canonical_user_id 或 self.id）
        root_id_subq = (
            select(func.coalesce(User.canonical_user_id, User.id))
            .where(User.id == user_id)
            .scalar_subquery()
        )

        # 子查詢 2：抓所有 alias group 成員（id == root OR canonical_user_id == root）
        return select(User.id).where(
            or_(
                User.id == root_id_subq,
                User.canonical_user_id == root_id_subq,
            )
        )

    @classmethod
    def get_user_accessible_project_ids(cls, user_id: int) -> Select:
        """
        取得使用者（含 alias group）可存取的專案 ID 子查詢。

        v2 (2026-05-06, TaskB)：
            user_id 自動展開為整個 alias group，未合併的同人多帳號相互可見。

        Args:
            user_id: 使用者 ID（可為 alias group 內任一）

        Returns:
            可用於 .in_() 的子查詢
        """
        from app.extended.models import project_user_assignment

        alias_ids = cls.get_alias_group_subquery(user_id)

        return select(
            project_user_assignment.c.project_id
        ).where(
            and_(
                project_user_assignment.c.user_id.in_(alias_ids),
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
        檢查使用者（含 alias group）是否有權限存取特定專案。

        v2 (2026-05-06, TaskB)：
            user_id 展開到整組 alias，任一 alias 有 project assignment 即視為有權限。

        Args:
            db: 資料庫 session
            user_id: 使用者 ID
            project_id: 專案 ID

        Returns:
            True 如果有權限，否則 False
        """
        from app.extended.models import project_user_assignment

        alias_ids = cls.get_alias_group_subquery(user_id)

        result = await db.execute(
            select(exists().where(
                and_(
                    project_user_assignment.c.project_id == project_id,
                    project_user_assignment.c.user_id.in_(alias_ids),
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

        logger.info(f"[RLS] 使用者 {user_id} 執行專案查詢（非管理員，套用行級別過濾，含 alias group 展開）")

        # v2 (2026-05-06, TaskB)：展開 alias group，未合併的同人多帳號相互可見
        alias_ids = cls.get_alias_group_subquery(user_id)

        return query.where(
            exists().where(
                and_(
                    project_user_assignment.c.project_id == project_model.id,
                    project_user_assignment.c.user_id.in_(alias_ids),
                    project_user_assignment.c.status.in_(cls.ACTIVE_ASSIGNMENT_STATUSES)
                )
            )
        )

    # P-1 (2026-05-06)：admin 角色對齊集中於 _ADMIN_ROLES 常數，
    # 防止「DB role='admin' 但 is_admin=False」造成 admin 帳號被當一般使用者
    # （事故：李昭德 id=19 role='admin', is_admin=False → 看不到自己參與的專案 doc）
    _ADMIN_ROLES = frozenset({"admin", "superuser"})

    @classmethod
    def is_user_admin(cls, user: Optional["User"]) -> bool:
        """
        檢查使用者是否為管理員（is_admin / is_superuser / role 三路同步認定）

        Args:
            user: 使用者物件

        Returns:
            True 如果是管理員或超級使用者
        """
        if user is None:
            return False
        if getattr(user, 'is_admin', False) or getattr(user, 'is_superuser', False):
            return True
        # role 欄位 fallback（資料修齊前的相容防線）
        role = (getattr(user, 'role', None) or "").lower()
        return role in cls._ADMIN_ROLES

    @classmethod
    def get_user_rls_flags(cls, user: Optional["User"]) -> tuple:
        """
        取得使用者的 RLS 標誌

        Args:
            user: 使用者物件

        Returns:
            (user_id, is_admin, is_superuser) 元組

        v2 (2026-05-06)：is_admin / is_superuser 都以 _ADMIN_ROLES 對齊，
        防止 boolean 欄位與 role 欄位不一致造成的 RLS 誤判。
        """
        if user is None:
            return (None, False, False)

        user_id = getattr(user, 'id', None)
        is_admin = bool(getattr(user, 'is_admin', False))
        is_superuser = bool(getattr(user, 'is_superuser', False))
        role = (getattr(user, 'role', None) or "").lower()

        # role fallback：DB 資料尚未對齊時，從 role 欄位推導
        if not is_superuser and role == "superuser":
            is_superuser = True
        if not is_admin and role in cls._ADMIN_ROLES:
            is_admin = True

        return (user_id, is_admin, is_superuser)
