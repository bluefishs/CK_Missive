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
        from app.extended.models.core import ContractProject

        alias_ids = cls.get_alias_group_subquery(user_id)

        cond = and_(
            project_user_assignment.c.user_id.in_(alias_ids),
            project_user_assignment.c.status.in_(cls.ACTIVE_ASSIGNMENT_STATUSES)
        )

        # 直接綁 project_id 的指派
        by_project = select(
            project_user_assignment.c.project_id
        ).where(and_(cond, project_user_assignment.c.project_id.isnot(None)))

        # ⚠️ 2026-08-29：只比 `project_id` 會漏掉**以 case_code 指派**的人。
        #
        # `project_user_assignment.project_id` 是 nullable —— 邀標階段的案件
        # 還沒成案、沒有 contract_project 可綁，所以那時只能寫 case_code
        # （該表的 `case_code` 欄位註解寫著「未成案時透過此欄關聯」）。
        #
        # 實測（2026-08-29 晚，owner 回報「/contract-cases 一堆 02承攬報價
        # 無對應承辦同仁」）：139 件 02 承攬案件中，**65 件只有 case_code 指派**
        # ⇒ 那 65 件的承辦在自己的案件列表裡**看不到自己的案子**。
        #
        # 成因是同日的承辦回填（依舊編號代碼補 115 件）只寫 case_code ——
        # 那個寫法本身是對的（指派掛在案號上，跨成案前後都成立），
        # **錯的是這裡只認一條路**。同族第三處：
        # `quotation_document.py`（08-21 修）／`filing_gap.py`（08-29 修）。
        by_case = select(
            ContractProject.id
        ).select_from(
            project_user_assignment.join(
                ContractProject,
                ContractProject.case_code == project_user_assignment.c.case_code,
            )
        ).where(cond)

        return by_project.union(by_case)

    @classmethod
    def get_user_accessible_case_codes(cls, user_id: int) -> Select:
        """使用者（含 alias group）可存取的 **case_code** 子查詢。

        ## 為什麼需要 case_code 版而不是沿用 project_id 版

        報價單以 `case_code` 為鍵，而且**可以在成案之前就存在**
        （邀標／報價階段還沒有 contract_project 可綁）。
        用 project_id 版會漏掉那一批 —— 那正是本 repo 2026-08-29
        修過四處、隔一輪才發現還有兩處的同族缺陷。

        ## 兩條來源都要（與 get_user_accessible_project_ids 對稱）

        · 指派直接寫 `case_code`（未成案時唯一可寫的欄位）
        · 指派寫 `project_id` → 反查該專案的 case_code

        **不重寫 alias 展開** —— 共用 `get_alias_group_subquery`，
        與 `apply_project_rls` 同一套判定。

        Returns:
            可用於 `.in_()` 的子查詢
        """
        from app.extended.models import project_user_assignment
        from app.extended.models.core import ContractProject

        alias_ids = cls.get_alias_group_subquery(user_id)
        cond = and_(
            project_user_assignment.c.user_id.in_(alias_ids),
            project_user_assignment.c.status.in_(cls.ACTIVE_ASSIGNMENT_STATUSES),
        )

        by_case = select(project_user_assignment.c.case_code).where(
            and_(cond, project_user_assignment.c.case_code.isnot(None))
        )
        by_project = select(ContractProject.case_code).where(
            and_(
                ContractProject.case_code.isnot(None),
                ContractProject.id.in_(
                    select(project_user_assignment.c.project_id).where(
                        and_(cond, project_user_assignment.c.project_id.isnot(None))
                    )
                ),
            )
        )
        return by_case.union(by_project)

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

        # ⚠️ 2026-08-29：`project_id` 與 `case_code` 兩條路都要認 ——
        # 邀標階段的指派沒有 project_id 可寫（案件還沒成案），
        # 成案後那筆指派仍然只有 case_code。詳見 `get_user_accessible_project_ids`。
        from app.extended.models.core import ContractProject

        case_code_of = (
            select(ContractProject.case_code)
            .where(ContractProject.id == project_id)
            .scalar_subquery()
        )
        result = await db.execute(
            select(exists().where(
                and_(
                    or_(
                        project_user_assignment.c.project_id == project_id,
                        project_user_assignment.c.case_code == case_code_of,
                    ),
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

        # ⚠️ 2026-08-29：這一處是**承攬案件列表**的過濾器 —— 只認 `project_id`
        # 的話，指派只掛在 `case_code` 上的承辦會在自己的列表裡看不到自己的案子。
        # 實測當日：139 件 02 承攬案件裡 65 件只有 case_code 指派。
        #
        # ⚠️ 同族第五、六處。我在同一天內修了四處（quotation_document 08-21／
        # filing_gap／project_repository／get_user_accessible_project_ids），
        # **而這個檔案裡剩下的兩處是隔一輪複查才發現的** ——
        # 當天才寫下「同族修法要先數清楚有幾處再動手」，然後又犯了同一件事。
        # 教訓的形態是：修完第一處之後要 grep 整個檔案，不是憑印象。
        return query.where(
            exists().where(
                and_(
                    or_(
                        project_user_assignment.c.project_id == project_model.id,
                        project_user_assignment.c.case_code == project_model.case_code,
                    ),
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
