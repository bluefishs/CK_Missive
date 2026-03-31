"""
角色權限與系統權限管理 API 端點

拆分自 user_management.py
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select as sa_select

from app.core.dependencies import get_async_db, require_admin
from app.extended.models import User
from app.services.audit_service import AuditService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


# === 權限預設清單 ===

@router.post("/permissions/available", summary="取得可用權限列表")
async def get_available_permissions(
    admin_user: User = Depends(require_admin())
):
    """取得系統中所有可用的權限列表 (管理員功能) - POST-only"""
    return {
        "permissions": [
            "documents:read", "documents:create", "documents:edit",
            "documents:delete", "documents:export",
            "projects:read", "projects:create", "projects:edit", "projects:delete",
            "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
            "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
            "admin:users", "admin:settings", "admin:database", "admin:site_management",
            "reports:view", "reports:export",
            "calendar:read", "calendar:edit", "notifications:read"
        ],
        "roles": [
            {"name": "unverified", "display_name": "未驗證者", "default_permissions": []},
            {
                "name": "user", "display_name": "一般使用者",
                "default_permissions": [
                    "documents:read", "projects:read", "agencies:read",
                    "vendors:read", "calendar:read", "reports:view"
                ]
            },
            {
                "name": "admin", "display_name": "管理員",
                "default_permissions": [
                    "documents:read", "documents:create", "documents:edit", "documents:delete",
                    "projects:read", "projects:create", "projects:edit", "projects:delete",
                    "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
                    "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
                    "admin:users", "admin:settings", "admin:site_management",
                    "reports:view", "reports:export",
                    "calendar:read", "calendar:edit"
                ]
            },
            {"name": "superuser", "display_name": "超級管理員", "default_permissions": ["*"]}
        ]
    }


# === 角色權限管理 ===

# 角色預設權限 (SSOT 定義)
_ROLE_DEFAULTS: dict[str, dict] = {
    "unverified": {
        "name_zh": "未驗證者", "name_en": "Unverified",
        "description_zh": "尚未通過管理員驗證的帳號",
        "default_permissions": [],
    },
    "user": {
        "name_zh": "一般使用者", "name_en": "User",
        "description_zh": "一般使用者，可瀏覽公文、專案等基本資料",
        "default_permissions": [
            "documents:read", "projects:read", "agencies:read",
            "vendors:read", "calendar:read", "reports:view",
        ],
    },
    "admin": {
        "name_zh": "管理員", "name_en": "Admin",
        "description_zh": "具備完整讀寫權限，可管理使用者與系統設定",
        "default_permissions": [
            "documents:read", "documents:create", "documents:edit", "documents:delete", "documents:export",
            "projects:read", "projects:create", "projects:edit", "projects:delete",
            "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
            "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
            "admin:users", "admin:settings", "admin:site_management",
            "reports:view", "reports:export", "calendar:read", "calendar:edit",
        ],
    },
    "superuser": {
        "name_zh": "超級管理員", "name_en": "Superuser",
        "description_zh": "最高權限角色，擁有所有權限",
        "default_permissions": ["*"],
    },
}


@router.post("/roles/{role}/permissions/detail", summary="取得角色預設權限")
async def get_role_permissions(
    role: str,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin()),
):
    """取得指定角色的預設權限配置 - POST-only"""
    if role not in _ROLE_DEFAULTS:
        raise HTTPException(status_code=404, detail=f"角色 '{role}' 不存在")

    base = _ROLE_DEFAULTS[role]

    # 檢查是否有自訂覆蓋 (SiteConfiguration)
    from app.extended.models.system import SiteConfiguration
    result = await db.execute(
        sa_select(SiteConfiguration).where(
            SiteConfiguration.key == f"role_permissions:{role}",
            SiteConfiguration.is_active == True,  # noqa: E712
        )
    )
    override = result.scalar_one_or_none()

    permissions = json.loads(override.value) if override else base["default_permissions"]

    return {
        "role": role,
        "name_zh": base["name_zh"],
        "name_en": base["name_en"],
        "description_zh": base["description_zh"],
        "permissions": permissions,
        "is_customized": override is not None,
    }


@router.post("/roles/{role}/permissions/update", summary="更新角色預設權限")
async def update_role_permissions(
    role: str,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin()),
    *,
    body: dict,
):
    """更新指定角色的預設權限配置 - POST-only

    Body: { "permissions": ["documents:read", ...] }
    """
    if role not in _ROLE_DEFAULTS:
        raise HTTPException(status_code=404, detail=f"角色 '{role}' 不存在")
    if role == "superuser":
        raise HTTPException(status_code=403, detail="超級管理員權限不可修改")

    new_permissions = body.get("permissions", [])
    if not isinstance(new_permissions, list):
        raise HTTPException(status_code=422, detail="permissions 必須為字串陣列")

    from app.extended.models.system import SiteConfiguration
    from sqlalchemy import func as sa_func

    config_key = f"role_permissions:{role}"
    result = await db.execute(
        sa_select(SiteConfiguration).where(SiteConfiguration.key == config_key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = json.dumps(new_permissions)
        existing.updated_at = sa_func.now()
        existing.is_active = True
    else:
        new_config = SiteConfiguration(
            key=config_key,
            value=json.dumps(new_permissions),
            description=f"角色 {role} 自訂權限",
            category="role_permissions",
        )
        db.add(new_config)

    await db.commit()

    # 審計記錄
    try:
        audit = AuditService(db)
        await audit.log(
            user_id=admin_user.id,
            action="update_role_permissions",
            resource_type="role",
            resource_id=role,
            details={"permissions": new_permissions},
        )
    except Exception:
        pass  # 審計失敗不阻擋主流程

    logger.info(f"[ROLE_PERM] 角色權限更新: role={role}, by={admin_user.email}, perms={len(new_permissions)}")

    return {
        "success": True,
        "role": role,
        "permissions": new_permissions,
        "message": f"角色 '{_ROLE_DEFAULTS[role]['name_zh']}' 權限已更新",
    }


@router.post("/roles/list", summary="列出所有角色及其權限")
async def list_roles(
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin()),
):
    """列出所有角色及其預設/自訂權限 - POST-only"""
    from app.extended.models.system import SiteConfiguration

    # 批次取得所有自訂覆蓋
    result = await db.execute(
        sa_select(SiteConfiguration).where(
            SiteConfiguration.key.like("role_permissions:%"),
            SiteConfiguration.is_active == True,  # noqa: E712
        )
    )
    overrides = {
        row.key.replace("role_permissions:", ""): json.loads(row.value)
        for row in result.scalars().all()
    }

    roles = []
    for role_key, info in _ROLE_DEFAULTS.items():
        custom = overrides.get(role_key)
        roles.append({
            "role": role_key,
            "name_zh": info["name_zh"],
            "name_en": info["name_en"],
            "description_zh": info["description_zh"],
            "permissions": custom if custom is not None else info["default_permissions"],
            "is_customized": custom is not None,
        })

    return {"roles": roles, "total": len(roles)}
