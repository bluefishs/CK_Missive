#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用者管理 API 端點

使用統一回應格式和錯誤處理機制。
資料存取透過 UserRepository 進行，遵循 Repository Pattern。

@version 3.0.0 - 使用 UserRepository 取代直接 ORM 查詢
@date 2026-02-06
"""
from fastapi import APIRouter, Depends, status, Body
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    UserCreate, UserUpdate, UserStatusUpdate,
    UserResponse, UserListResponse,
    UserListQuery
)
from app.schemas.common import (
    PaginationMeta,
    DeleteResponse,
)
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ForbiddenException,
)
from app.core.dependencies import require_admin
from app.core.auth_service import AuthService

router = APIRouter()


def get_password_hash(password: str) -> str:
    """密碼加密 - 委託給 AuthService"""
    return AuthService.get_password_hash(password)


def get_user_repository(db: AsyncSession = Depends(get_async_db)) -> UserRepository:
    """
    取得 UserRepository 實例（工廠模式）

    每個請求建立新的 Repository 實例，db session 在建構時注入。
    """
    return UserRepository(db)


# 注意：UserListQuery 已統一定義於 app/schemas/user.py


# ============================================================================
# 使用者列表 API
# ============================================================================

@router.post(
    "/list",
    response_model=UserListResponse,
    summary="查詢使用者列表",
    description="使用統一分頁格式查詢使用者列表"
)
async def get_users(
    query: UserListQuery = Body(default=UserListQuery()),
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(require_admin())
):
    """
    查詢使用者列表（POST-only 資安機制）

    回應格式：
    ```json
    {
        "success": true,
        "items": [...],
        "pagination": {
            "total": 100,
            "page": 1,
            "limit": 20,
            "total_pages": 5,
            "has_next": true,
            "has_prev": false
        }
    }
    ```
    """
    users, total = await user_repo.get_users_filtered(
        role=query.role,
        is_active=query.is_active,
        department=query.department,
        search=query.search,
        sort_by=query.sort_by,
        sort_order=query.sort_order.value,
        page=query.page,
        limit=query.limit,
    )

    # 轉換為回應格式
    items = [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role or "user",
            is_active=user.is_active if user.is_active is not None else True,
            last_login=user.last_login,
            created_at=user.created_at,
            department=user.department,
            position=user.position
        )
        for user in users
    ]

    return UserListResponse(
        items=items,
        pagination=PaginationMeta.create(
            total=total,
            page=query.page,
            limit=query.limit
        )
    )


# ============================================================================
# CRUD API
# ============================================================================

@router.post(
    "/{user_id}/detail",
    response_model=UserResponse,
    summary="取得使用者詳情"
)
async def get_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(require_admin())
):
    """取得指定使用者的詳細資訊"""
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise NotFoundException(resource="使用者", resource_id=user_id)

    return user


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立新使用者"
)
async def create_user(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(require_admin())
):
    """建立新使用者"""
    # 檢查帳號是否已存在
    if await user_repo.check_username_exists(user_data.username):
        raise ConflictException(
            message=f"帳號 '{user_data.username}' 已存在",
            field="username",
            value=user_data.username
        )

    # 檢查 Email 是否已存在
    if await user_repo.check_email_exists(user_data.email):
        raise ConflictException(
            message=f"Email '{user_data.email}' 已被使用",
            field="email",
            value=user_data.email
        )

    # 建立使用者（需要密碼加密，因此手動建構 User 物件）
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role or '專案PM',
        is_active=user_data.is_active,
        password_hash=get_password_hash(user_data.password),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    user_repo.db.add(new_user)
    await user_repo.db.commit()
    await user_repo.db.refresh(new_user)

    return new_user


@router.post(
    "/{user_id}/update",
    response_model=UserResponse,
    summary="更新使用者"
)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(require_admin())
):
    """更新指定使用者的資訊"""
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise NotFoundException(resource="使用者", resource_id=user_id)

    # 更新欄位 (只更新有提供的欄位)
    update_data = user_data.model_dump(exclude_unset=True)

    # 如果有更新密碼，需要加密
    if 'password' in update_data and update_data['password']:
        user.password_hash = get_password_hash(update_data['password'])
        del update_data['password']

    # 檢查 Email 是否與其他使用者重複
    if 'email' in update_data and update_data['email'] != user.email:
        if await user_repo.check_email_exists(update_data['email'], exclude_id=user_id):
            raise ConflictException(
                message=f"Email '{update_data['email']}' 已被使用",
                field="email",
                value=update_data['email']
            )

    # 套用更新
    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.now()

    await user_repo.db.commit()
    await user_repo.db.refresh(user)

    return user


@router.post(
    "/{user_id}/delete",
    response_model=DeleteResponse,
    summary="刪除使用者"
)
async def delete_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(require_admin())
):
    """刪除指定使用者"""
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise NotFoundException(resource="使用者", resource_id=user_id)

    # 防止刪除超級管理員
    if user.is_superuser:
        raise ForbiddenException(message="無法刪除超級管理員")

    await user_repo.delete(user_id)

    return DeleteResponse(
        success=True,
        message="使用者已刪除",
        deleted_id=user_id
    )


@router.post(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="修改使用者狀態"
)
async def update_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(require_admin())
):
    """啟用或停用使用者"""
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise NotFoundException(resource="使用者", resource_id=user_id)

    # 防止停用超級管理員
    if user.is_superuser and not status_data.is_active:
        raise ForbiddenException(message="無法停用超級管理員")

    user.is_active = status_data.is_active
    user.updated_at = datetime.now()

    await user_repo.db.commit()
    await user_repo.db.refresh(user)

    return user
