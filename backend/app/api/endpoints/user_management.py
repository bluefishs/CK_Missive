"""
使用者管理 API 端點 (User CRUD)

v5.0.0 - 2026-03-30
- 拆分: 權限/會話/LINE → user_permissions.py
- 拆分: 角色權限 → role_permissions.py
- 本檔僅保留使用者 CRUD (list/create/detail/update/delete)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth_service import AuthService
from app.core.dependencies import get_async_db, require_admin
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    UserResponse, UserUpdate, UserListResponse, UserSearchParams, UserRegister,
)
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
