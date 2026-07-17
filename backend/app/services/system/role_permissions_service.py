"""RolePermissionsService — ADR-0034 動態 role permissions 業務邏輯。"""
import logging
from typing import Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.role_permissions_repository import RolePermissionsRepository

logger = logging.getLogger(__name__)


# 業務 endpoint 用到的 permission（與 site_navigation_items.permission_required 之外的補集）
# 這份清單應該從 require_permission(...) decorator 反向掃出來，但短期 hardcode 已知 set。
# 未來改為「啟動時 scan FastAPI routes 找 require_permission」自動產出。
_BUSINESS_PERMISSIONS = {
    # documents
    "documents:read", "documents:create", "documents:edit", "documents:delete",
    # projects / agencies / vendors
    "projects:read", "projects:create", "projects:edit", "projects:delete",
    "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
    "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
    # calendar
    "calendar:read", "calendar:edit",
    # reports（路 A 細分授權，2026-05-06）
    "reports:view",          # 報表選單可見（總開關）
    "reports:stats:view",    # 統計報表
    "reports:tender:view",   # 政府標案
    "reports:finance:view",  # 專案財務
    "reports:erp:view",      # ERP 財務
    "reports:assets:view",   # 資產管理
    "reports:export",        # 匯出（橫切）
    # system docs
    "system_docs:read", "system_docs:create", "system_docs:edit", "system_docs:delete",
    # operational（營運帳目；前端 hasPermission 有檢查 write/approve，2026-07-17 C2 補進 SSOT）
    "operational:read", "operational:write", "operational:approve",
    # admin
    "admin:users", "admin:settings", "admin:site_management", "admin:database",
}


class RolePermissionsService:
    """動態 role permissions 業務層。

    - 列表 / 單一查詢：委派 Repository
    - update：含 actor audit + 後續 user.permissions sync 提示
    - available_permissions：聚合 navigation_items + 業務 endpoint set
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RolePermissionsRepository(db)

    async def list_all_roles(self) -> List[Dict]:
        """回傳所有 role 配置 dict（給前端介面）。"""
        rows = await self.repo.list_all()
        return [self._to_dict(r) for r in rows]

    async def get_role(self, role: str) -> Optional[Dict]:
        """取單一 role 配置 dict。"""
        rp = await self.repo.get_by_role(role)
        if not rp:
            return None
        return self._to_dict(rp)

    async def update_role_permissions(
        self,
        role: str,
        permissions: List[str],
        actor_id: int,
    ) -> Dict:
        """更新 role 的 permissions（含 actor audit）。"""
        rp = await self.repo.update_permissions(role, permissions, actor_id)
        return self._to_dict(rp)

    async def get_available_permissions(self) -> Dict:
        """回傳系統內所有可分派的 permission keys（給編輯介面下拉用）。

        來源：
        1. site_navigation_items.permission_required 出現過的
        2. 業務 endpoint 已宣告的 (_BUSINESS_PERMISSIONS)
        3. 已被任一 role 指派的（追溯既有配置）

        並標記哪些 permissions「已被某個 role 指派」、哪些「尚未被任何 role 分派」（待分派紅點）。
        """
        from_nav = await self.repo.collect_known_permissions_from_navigation()
        assigned = await self.repo.collect_all_assigned_permissions()

        all_perms = from_nav | _BUSINESS_PERMISSIONS | assigned

        # 分類：已分派（at least one role 含有）vs 未分派（無 role 含有）
        unassigned = sorted(all_perms - assigned)
        return {
            "all": sorted(all_perms),
            "assigned": sorted(assigned),
            "unassigned": unassigned,  # 給 UI 紅點提示
            "from_navigation_items": sorted(from_nav),
            "from_business_endpoints": sorted(_BUSINESS_PERMISSIONS),
            "total_count": len(all_perms),
            "unassigned_count": len(unassigned),
        }

    async def get_navigation_tree_with_permissions(
        self,
        role: Optional[str] = None,
    ) -> Dict:
        """回傳完整 site_navigation_items 階層樹 + 每節點對應 permission_required。

        若提供 role，同時帶回該 role.permissions（給前端預勾用）。

        Returns:
            {
                "tree": [...],                # 階層節點（含 children 遞迴）
                "role": str | None,
                "role_permissions": [...],
                "perm_to_nav": {perm: [{id, key, title}]}  # 反查 perm 出現在哪些 nav
            }
        """
        from sqlalchemy import text

        result = await self.db.execute(text("""
            SELECT id, parent_id, key, title, path, level, sort_order,
                   is_enabled, is_visible, permission_required
            FROM site_navigation_items
            ORDER BY parent_id NULLS FIRST, sort_order, id
        """))
        rows = result.fetchall()

        import json as _json
        items_by_id: Dict = {}
        for r in rows:
            try:
                perms = _json.loads(r.permission_required) if r.permission_required else []
                if not isinstance(perms, list):
                    perms = []
            except Exception:
                perms = []
            items_by_id[r.id] = {
                "id": r.id,
                "parent_id": r.parent_id,
                "key": r.key,
                "title": r.title,
                "path": r.path,
                "level": r.level,
                "sort_order": r.sort_order,
                "is_enabled": bool(r.is_enabled),
                "is_visible": bool(r.is_visible),
                "permission_required": perms,
                "children": [],
            }

        roots: list = []
        for item in items_by_id.values():
            if item["parent_id"] is None:
                roots.append(item)
            else:
                parent = items_by_id.get(item["parent_id"])
                if parent is not None:
                    parent["children"].append(item)

        perm_to_nav: Dict[str, list] = {}
        for item in items_by_id.values():
            for perm in item["permission_required"]:
                perm_to_nav.setdefault(perm, []).append({
                    "id": item["id"], "key": item["key"], "title": item["title"],
                })

        role_permissions: list = []
        is_wildcard = False
        if role:
            rp = await self.repo.get_by_role(role)
            if rp:
                role_permissions = list(rp.permissions or [])
                is_wildcard = role_permissions == ["*"]

        return {
            "tree": roots,
            "role": role,
            "role_permissions": role_permissions,
            "perm_to_nav": perm_to_nav,
            "is_wildcard": is_wildcard,
        }

    async def sync_users_to_role_permissions(
        self,
        role: str,
        actor_id: int,
        only_outdated: bool = True,
    ) -> Dict:
        """將指定 role 的所有 active user.permissions 同步為 role_permissions[role]。

        場景：在 /admin/permissions/{role} 修改 role 權限後，舊 user.permissions
        不會自動跟著動。本方法批次同步既有 user。
        """
        import json as _json
        from sqlalchemy import select, update
        from app.extended.models import User

        rp = await self.repo.get_by_role(role)
        if not rp:
            raise ValueError(f"role '{role}' 不存在")

        target_perms = list(rp.permissions or [])
        target_json = _json.dumps(target_perms)
        target_sorted = sorted(target_perms)

        result = await self.db.execute(
            select(User.id, User.email, User.full_name, User.permissions)
            .where(User.role == role, User.is_active == True)  # noqa: E712
        )
        users = result.fetchall()

        updated_users = []
        skipped_users = []

        for u in users:
            try:
                current_perms = sorted(_json.loads(u.permissions)) if u.permissions else []
            except Exception:
                current_perms = []

            if only_outdated and current_perms == target_sorted:
                skipped_users.append({"id": u.id, "email": u.email, "reason": "已對齊"})
                continue

            await self.db.execute(
                update(User).where(User.id == u.id).values(permissions=target_json)
            )
            updated_users.append({
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "before_count": len(current_perms),
                "after_count": len(target_perms),
            })

        await self.db.commit()
        logger.info(
            "[ROLE-PERM] Sync users role=%s by actor=%d: scanned=%d updated=%d skipped=%d",
            role, actor_id, len(users), len(updated_users), len(skipped_users),
        )
        return {
            "role": role,
            "scanned": len(users),
            "updated": len(updated_users),
            "skipped": len(skipped_users),
            "updated_users": updated_users,
            "skipped_users": skipped_users,
        }

    @staticmethod
    def _to_dict(rp) -> Dict:
        return {
            "role": rp.role,
            "permissions": list(rp.permissions or []),
            "can_login": bool(rp.can_login),
            "name_zh": rp.name_zh,
            "description_zh": rp.description_zh,
            "permission_count": len(rp.permissions) if rp.permissions else 0,
            "is_wildcard": rp.permissions == ["*"],
            "updated_at": rp.updated_at.isoformat() if rp.updated_at else None,
            "updated_by": rp.updated_by,
        }
