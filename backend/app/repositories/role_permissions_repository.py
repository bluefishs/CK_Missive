"""RolePermissionsRepository — ADR-0034 動態 role permissions 存取層。"""
import logging
from typing import List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import RolePermissions

logger = logging.getLogger(__name__)


class RolePermissionsRepository:
    """role_permissions 表 CRUD + 聚合查詢。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> List[RolePermissions]:
        """取所有 role 配置（給 PermissionManagementPage）。"""
        result = await self.db.execute(
            select(RolePermissions).order_by(RolePermissions.role)
        )
        return list(result.scalars().all())

    async def get_by_role(self, role: str) -> Optional[RolePermissions]:
        """取單一 role 配置。"""
        result = await self.db.execute(
            select(RolePermissions).where(RolePermissions.role == role)
        )
        return result.scalar_one_or_none()

    async def get_permissions(self, role: str) -> List[str]:
        """快速取單一 role 的 permissions（給 oauth login / 預設權限賦予用）。

        v2 增加 fallback：role_permissions 表查不到時回 [] 由 caller 決定 hardcode。
        """
        rp = await self.get_by_role(role)
        if not rp or not rp.permissions:
            return []
        return list(rp.permissions)

    async def update_permissions(
        self,
        role: str,
        permissions: List[str],
        actor_id: Optional[int] = None,
    ) -> Optional[RolePermissions]:
        """更新 role 的 permissions。

        Args:
            role: 目標 role（不可為 'superuser' — 由 wildcard 保護）
            permissions: 新 permissions list（去重 + 排序後寫入）
            actor_id: 操作者 user_id（audit log）

        Raises:
            ValueError: role 不存在或為 superuser
        """
        if role == "superuser":
            raise ValueError(
                "superuser permissions 為 wildcard ('*')，不可由介面修改"
            )

        rp = await self.get_by_role(role)
        if not rp:
            raise ValueError(f"role '{role}' 不存在於 role_permissions 表")

        # 去重 + 排序（提高一致性，方便 diff）
        cleaned = sorted(set(permissions))
        rp.permissions = cleaned
        rp.updated_by = actor_id

        await self.db.commit()
        await self.db.refresh(rp)
        logger.info(
            "[ROLE-PERM] role=%s permissions updated by user=%s (count=%d)",
            role, actor_id, len(cleaned),
        )
        return rp

    async def collect_known_permissions_from_navigation(self) -> Set[str]:
        """從 site_navigation_items.permission_required 抽出所有用到的 permissions。

        用於 /admin/role-permissions/available 端點，提示「目前系統會用到的權限全集」。
        """
        from sqlalchemy import text

        # permission_required 為 TEXT 欄位（存 JSON 字串），需 cast 為 jsonb
        result = await self.db.execute(text("""
            SELECT DISTINCT jsonb_array_elements_text(permission_required::jsonb) AS perm
            FROM site_navigation_items
            WHERE permission_required IS NOT NULL
              AND permission_required != ''
              AND permission_required != '[]'
              AND jsonb_typeof(permission_required::jsonb) = 'array'
              AND jsonb_array_length(permission_required::jsonb) > 0
        """))
        perms = {row[0] for row in result.fetchall() if row[0]}
        return perms

    async def collect_all_assigned_permissions(self) -> Set[str]:
        """取所有 role 中被指派過的 permissions union，輔助偵測 dead permission。"""
        result = await self.db.execute(
            select(RolePermissions.permissions)
        )
        all_perms: Set[str] = set()
        for row in result.fetchall():
            perms = row[0]
            if perms and isinstance(perms, list):
                all_perms.update(p for p in perms if p != "*")
        return all_perms
