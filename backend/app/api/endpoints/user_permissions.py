"""
使用者權限與會話管理 API 端點

拆分自 user_management.py
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
    UserResponse, UserPermissions, PermissionCheck, UserSessionsResponse,
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
