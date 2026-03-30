"""
使用者管理與權限管理 API 端點

v4.0.0 - 2026-02-24
- 所有 DB 操作遷移至 UserRepository
- 使用統一 DI 模式 (get_user_repository)
- 移除端點中的直接 db.execute() 呼叫
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select as sa_select

from app.core.auth_service import AuthService
from app.core.dependencies import get_async_db, require_admin
from app.api.endpoints.auth import get_current_user
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    UserResponse, UserUpdate, UserListResponse, UserSearchParams,
    UserPermissions, PermissionCheck, UserSessionsResponse, UserRegister,
)
from app.schemas.admin import AdminLineBindRequest
from app.extended.models import User
from app.services.audit_service import AuditService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


def get_user_repository(db: AsyncSession = Depends(get_async_db)) -> UserRepository:
    """取得 UserRepository 實例"""
    return UserRepository(db)


# === 使用者管理 ===

@router.post("/users/list", response_model=UserListResponse, summary="取得使用者列表")
async def get_users(
    params: UserSearchParams,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """取得使用者列表 (管理員功能) - POST-only"""
    users, total = await user_repo.get_users_filtered(
        role=params.role,
        is_active=params.is_active,
        search=params.q,
        page=params.page,
        limit=params.per_page,
    )

    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=params.page,
        per_page=params.per_page
    )


@router.post("/users", response_model=UserResponse, summary="新增使用者")
async def create_user(
    user_data: UserRegister,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """新增使用者 (管理員功能)"""
    if await user_repo.check_email_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該電子郵件已被使用"
        )

    if await user_repo.check_username_exists(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該使用者名稱已被使用"
        )

    password_hash = AuthService.get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        password_hash=password_hash,
        auth_provider="email",
        is_active=True,
        is_admin=False,
        role="user",
        email_verified=False,
        permissions='["documents:read", "projects:read", "agencies:read", "vendors:read", "calendar:read", "reports:view"]'
    )

    created_user = await user_repo.create_user(new_user)
    return UserResponse.model_validate(created_user)


@router.post("/users/{user_id}/detail", response_model=UserResponse, summary="取得指定使用者")
async def get_user_by_id(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """取得指定使用者詳細資訊 (管理員功能) - POST-only"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/update", response_model=UserResponse, summary="更新使用者資訊")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """更新使用者資訊 (管理員功能) - POST-only"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )

    # 記錄原始值用於審計
    old_data = {
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "role": user.role
    }

    update_data = user_update.model_dump(exclude_unset=True)

    # 唯一性檢查
    if "email" in update_data and update_data["email"] != user.email:
        if await user_repo.check_email_exists(update_data["email"], exclude_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="該電子郵件已被使用"
            )

    if "username" in update_data and update_data["username"] != user.username:
        if await user_repo.check_username_exists(update_data["username"], exclude_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="該使用者名稱已被使用"
            )

    # 透過 Repository 執行更新
    updated_user = await user_repo.update_and_refresh(user_id, **update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )

    # 計算實際變更並記錄審計
    changes = {}
    for key, new_value in update_data.items():
        old_value = old_data.get(key)
        if old_value != new_value:
            changes[key] = {"old": old_value, "new": new_value}

    if changes:
        if "is_active" in changes:
            event_type = "ACCOUNT_ACTIVATED" if update_data.get("is_active") else "ACCOUNT_DEACTIVATED"
            await AuditService.log_auth_event(
                event_type=event_type,
                user_id=user_id,
                email=user.email,
                details={"admin_id": admin_user.id, "admin_name": admin_user.full_name},
                success=True
            )

        await AuditService.log_user_change(
            user_id=user_id,
            action="UPDATE",
            changes=changes,
            admin_id=admin_user.id,
            admin_name=admin_user.full_name
        )

    logger.info(f"[USER_MGMT] 使用者 {user_id} 已更新 by {admin_user.email}")
    return UserResponse.model_validate(updated_user)


@router.post("/users/{user_id}/delete", summary="刪除使用者")
async def delete_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """軟刪除使用者 (管理員功能) - POST-only"""
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無法刪除自己的帳號"
        )

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )

    user_email = user.email
    success = await user_repo.soft_delete(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刪除使用者失敗"
        )
    await user_repo.db.commit()

    # 記錄審計
    await AuditService.log_auth_event(
        event_type="ACCOUNT_DEACTIVATED",
        user_id=user_id,
        email=user_email,
        details={"admin_id": admin_user.id, "admin_name": admin_user.full_name, "action": "soft_delete"},
        success=True
    )
    await AuditService.log_user_change(
        user_id=user_id,
        action="DELETE",
        changes={"is_active": {"old": True, "new": False}},
        admin_id=admin_user.id,
        admin_name=admin_user.full_name
    )

    logger.info(f"[USER_MGMT] 使用者 {user_id} ({user_email}) 已刪除 by {admin_user.email}")
    return {"message": "使用者已刪除"}


# === 權限管理 ===

@router.post("/users/{user_id}/permissions/detail", response_model=UserPermissions, summary="取得使用者權限")
async def get_user_permissions(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """取得指定使用者的權限列表 (管理員功能) - POST-only"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )

    permissions = []
    if user.permissions:
        try:
            permissions = json.loads(user.permissions)
        except json.JSONDecodeError:
            permissions = []

    return UserPermissions(
        user_id=user.id,
        permissions=permissions,
        role=user.role
    )


@router.post("/users/{user_id}/permissions/update", response_model=UserPermissions, summary="更新使用者權限")
async def update_user_permissions(
    user_id: int,
    permissions_data: UserPermissions,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """更新指定使用者的權限 (管理員功能) - POST-only"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )

    # 記錄原始權限
    old_permissions = []
    if user.permissions:
        try:
            old_permissions = json.loads(user.permissions)
        except json.JSONDecodeError:
            old_permissions = []
    old_role = user.role

    # 透過 Repository 執行更新
    permissions_json = json.dumps(permissions_data.permissions)
    await user_repo.update_fields(user_id, permissions=permissions_json, role=permissions_data.role)
    await user_repo.db.commit()

    # 記錄審計
    await AuditService.log_permission_change(
        user_id=user_id,
        action="PERMISSION_UPDATE",
        old_permissions=old_permissions,
        new_permissions=permissions_data.permissions,
        old_role=old_role,
        new_role=permissions_data.role,
        admin_id=admin_user.id,
        admin_name=admin_user.full_name
    )

    logger.info(f"[USER_MGMT] 使用者 {user_id} 權限已更新 by {admin_user.email}")
    return permissions_data


@router.post("/permissions/check", summary="檢查權限")
async def check_permission(
    permission_check: PermissionCheck,
    current_user: User = Depends(get_current_user)
):
    """檢查當前使用者是否具有指定權限"""
    has_permission = AuthService.check_permission(current_user, permission_check.permission)

    return {
        "permission": permission_check.permission,
        "resource": permission_check.resource,
        "granted": has_permission,
        "user_id": current_user.id,
        "user_role": current_user.role
    }


# === 會話管理 ===

@router.post("/users/{user_id}/sessions/list", response_model=UserSessionsResponse, summary="取得使用者會話")
async def get_user_sessions(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """取得指定使用者的所有會話 (管理員功能) - POST-only"""
    sessions = await user_repo.get_user_sessions(user_id)

    current_session_id = None
    for session in sessions:
        if session.is_active:
            current_session_id = session.id
            break

    return UserSessionsResponse(
        sessions=[{
            "id": session.id,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "device_info": session.device_info,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "is_active": session.is_active
        } for session in sessions],
        current_session_id=current_session_id or 0
    )


@router.post("/sessions/{session_id}/revoke", summary="撤銷會話")
async def revoke_user_session(
    session_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """撤銷指定會話 (管理員功能) - POST-only"""
    session = await user_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="會話不存在"
        )

    success = await AuthService.revoke_session(user_repo.db, session.token_jti)

    if success:
        return {"message": "會話已撤銷"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="撤銷會話失敗"
        )


# === 帳號解鎖 ===

@router.post("/users/{user_id}/unlock", response_model=UserResponse, summary="管理員解鎖帳號")
async def admin_unlock_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """管理員解鎖被鎖定的使用者帳號 (重置登入失敗次數) - POST-only"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="使用者不存在")

    if not user.locked_until and (user.failed_login_attempts or 0) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此帳號未被鎖定")

    old_attempts = user.failed_login_attempts
    old_locked = user.locked_until
    await user_repo.update_fields(user_id, failed_login_attempts=0, locked_until=None)
    await user_repo.db.commit()

    updated_user = await user_repo.get_by_id(user_id)

    await AuditService.log_user_change(
        user_id=user_id,
        action="ACCOUNT_UNLOCK",
        changes={
            "failed_login_attempts": {"old": old_attempts, "new": 0},
            "locked_until": {"old": str(old_locked) if old_locked else None, "new": None},
        },
        admin_id=admin_user.id,
        admin_name=admin_user.full_name
    )

    logger.info(f"[USER_MGMT] 管理員解鎖帳號: user={user_id} (was locked, {old_attempts} failed attempts) by {admin_user.email}")
    return UserResponse.model_validate(updated_user)


# === LINE 綁定管理 ===

@router.post("/users/{user_id}/line-bind", response_model=UserResponse, summary="管理員綁定 LINE")
async def admin_bind_line(
    user_id: int,
    bind_data: AdminLineBindRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """管理員手動綁定 LINE 帳號到指定使用者 - POST-only"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="使用者不存在")

    # 檢查 LINE ID 格式
    if not bind_data.line_user_id.startswith("U"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LINE User ID 格式錯誤 (應以 U 開頭)")

    # 檢查 LINE ID 是否已被其他帳號使用
    result = await user_repo.db.execute(
        sa_select(User).where(User.line_user_id == bind_data.line_user_id, User.id != user_id)
    )
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="此 LINE ID 已綁定到其他帳號")

    old_line_id = user.line_user_id
    await user_repo.update_fields(user_id, line_user_id=bind_data.line_user_id, line_display_name=bind_data.line_display_name or user.full_name)
    await user_repo.db.commit()

    updated_user = await user_repo.get_by_id(user_id)

    await AuditService.log_user_change(
        user_id=user_id,
        action="LINE_BIND",
        changes={"line_user_id": {"old": old_line_id, "new": bind_data.line_user_id}},
        admin_id=admin_user.id,
        admin_name=admin_user.full_name
    )

    logger.info(f"[USER_MGMT] 管理員綁定 LINE: user={user_id}, line_id={bind_data.line_user_id[:12]}... by {admin_user.email}")
    return UserResponse.model_validate(updated_user)


@router.post("/users/{user_id}/line-unbind", response_model=UserResponse, summary="管理員解除 LINE 綁定")
async def admin_unbind_line(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    admin_user: User = Depends(require_admin())
):
    """管理員解除指定使用者的 LINE 綁定 - POST-only"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="使用者不存在")

    if not user.line_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此使用者尚未綁定 LINE")

    old_line_id = user.line_user_id
    old_line_name = user.line_display_name
    await user_repo.update_fields(user_id, line_user_id=None, line_display_name=None)
    await user_repo.db.commit()

    updated_user = await user_repo.get_by_id(user_id)

    await AuditService.log_user_change(
        user_id=user_id,
        action="LINE_UNBIND",
        changes={"line_user_id": {"old": old_line_id, "new": None}, "line_display_name": {"old": old_line_name, "new": None}},
        admin_id=admin_user.id,
        admin_name=admin_user.full_name
    )

    logger.info(f"[USER_MGMT] 管理員解除 LINE: user={user_id} by {admin_user.email}")
    return UserResponse.model_validate(updated_user)


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
