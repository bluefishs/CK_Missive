#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用者管理 API 端點

使用統一回應格式和錯誤處理機制
"""
from fastapi import APIRouter, Depends, status, Body
from typing import Optional
from datetime import datetime
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.db.database import get_async_db
from app.extended.models import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserStatusUpdate,
    UserResponse, UserListResponse
)
from app.schemas.common import (
    PaginationMeta,
    DeleteResponse,
    SortOrder,
)
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ForbiddenException,
)
from app.core.dependencies import require_admin

router = APIRouter()

# 密碼加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """密碼加密"""
    return pwd_context.hash(password)


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class UserListQuery(BaseModel):
    """使用者列表查詢參數（統一格式）"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    role: Optional[str] = Field(None, description="角色篩選")
    is_active: Optional[bool] = Field(None, description="啟用狀態篩選")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.ASC, description="排序方向")


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
    db: AsyncSession = Depends(get_async_db),
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
    # 建立基本查詢
    db_query = select(User)
    count_query = select(func.count()).select_from(User)

    # 篩選條件
    if query.role:
        db_query = db_query.where(User.role == query.role)
        count_query = count_query.where(User.role == query.role)

    if query.is_active is not None:
        db_query = db_query.where(User.is_active == query.is_active)
        count_query = count_query.where(User.is_active == query.is_active)

    if query.search:
        search_filter = or_(
            User.username.ilike(f"%{query.search}%"),
            User.email.ilike(f"%{query.search}%"),
            User.full_name.ilike(f"%{query.search}%")
        )
        db_query = db_query.where(search_filter)
        count_query = count_query.where(search_filter)

    # 取得總數
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 計算 skip 值並排序
    skip = (query.page - 1) * query.limit

    # 排序
    sort_column = getattr(User, query.sort_by, User.id)
    if query.sort_order == SortOrder.DESC:
        sort_column = sort_column.desc()

    db_query = db_query.offset(skip).limit(query.limit).order_by(sort_column)
    result = await db.execute(db_query)
    users = result.scalars().all()

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
            created_at=user.created_at
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """取得指定使用者的詳細資訊"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """建立新使用者"""
    # 檢查帳號是否已存在
    existing = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            message=f"帳號 '{user_data.username}' 已存在",
            field="username",
            value=user_data.username
        )

    # 檢查 Email 是否已存在
    existing_email = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing_email.scalar_one_or_none():
        raise ConflictException(
            message=f"Email '{user_data.email}' 已被使用",
            field="email",
            value=user_data.email
        )

    # 建立使用者
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

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post(
    "/{user_id}/update",
    response_model=UserResponse,
    summary="更新使用者"
)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """更新指定使用者的資訊"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

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
        existing_email = await db.execute(
            select(User).where(
                and_(User.email == update_data['email'], User.id != user_id)
            )
        )
        if existing_email.scalar_one_or_none():
            raise ConflictException(
                message=f"Email '{update_data['email']}' 已被使用",
                field="email",
                value=update_data['email']
            )

    # 套用更新
    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.now()

    await db.commit()
    await db.refresh(user)

    return user


@router.post(
    "/{user_id}/delete",
    response_model=DeleteResponse,
    summary="刪除使用者"
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """刪除指定使用者"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException(resource="使用者", resource_id=user_id)

    # 防止刪除超級管理員
    if user.is_superuser:
        raise ForbiddenException(message="無法刪除超級管理員")

    await db.delete(user)
    await db.commit()

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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """啟用或停用使用者"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException(resource="使用者", resource_id=user_id)

    # 防止停用超級管理員
    if user.is_superuser and not status_data.is_active:
        raise ForbiddenException(message="無法停用超級管理員")

    user.is_active = status_data.is_active
    user.updated_at = datetime.now()

    await db.commit()
    await db.refresh(user)

    return user
