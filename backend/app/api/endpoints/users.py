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
from app.core.dependencies import require_auth, is_superuser_user, require_admin
from app.core.auth_service import AuthService

router = APIRouter()


def get_password_hash(password: str) -> str:
    """密碼加密 - 委託給 AuthService"""
    return AuthService.get_password_hash(password)


async def _has_other_active_superuser(user_repo, exclude_id: int) -> bool:
    """除了 exclude_id 之外，是否還有其他**可用**的超級管理員。

    「可用」＝ is_active 且是超管（旗標或 role 任一，與 is_superuser_user 同判準）。
    停用中的超管不算 —— 若把它算進來，就會出現「系統裡只剩一個停用的超管，
    卻允許把唯一能用的那個也停掉」的情況。
    """
    from sqlalchemy import select, or_, func
    from app.extended.models import User as UserModel
    stmt = select(func.count()).select_from(UserModel).where(
        UserModel.id != exclude_id,
        UserModel.is_active.is_(True),
        or_(UserModel.is_superuser.is_(True), UserModel.role == "superuser"),
    )
    return bool((await user_repo.db.execute(stmt)).scalar() or 0)


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
    "/assignable",
    summary="可指派人員（僅姓名等最小欄位）",
)
async def get_assignable_users(
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(require_auth()),
):
    """指派同仁用的人員清單 —— **只要登入就能取得**。

    owner 2026-08-20：「切換前述兩組帳號，皆僅顯示代號無姓名」
    （`/contract-cases/194/staff/create`）。

    # 根因

    那個頁面原本打 `/users/list`，而它是 `require_admin()`。
    以 `role='user'` 的帳號登入 ⇒ **403 ⇒ 選項為空**，
    而 AntD 的 Select 在 options 為空、value 有值時會直接顯示原始 value
    ⇒ 畫面上就是一個數字 id，也就是 owner 說的「代號」。

    「新增承辦同仁」是業務操作，不該只有管理員能做。

    # 為什麼另開端點而不是放寬 /users/list

    `/users/list` 回傳 last_login、department、角色與權限等資訊，
    對一般使用者開放不合適。這一支只回**指派需要的最小欄位**：
    id / full_name / username / email / is_active / canonical_user_id。

    分身欄位要給 —— 前端 `filterAssignableUsers` 靠它排除已合併的帳號，
    少了它同一個人會在下拉出現兩次（2026-08-04 的原始症狀）。

    email 也要給，理由不是「反正看得到」，而是**既有下拉的 label 就是
    `姓名 (email)`**（資產保管人、PM 承辦）。少給它，換資料源的當下
    畫面就會少一半資訊 —— 而 2026-08-04 那次「同仁變成代碼」的成因
    正是我把 label 從 `姓名 (email)` 簡化成只剩姓名。公務信箱是同一個
    系統內的同事聯絡方式，與 last_login／department 不同層級。
    """
    # `get_active_users` 本身就只回在職者 —— 指派清單本來就不該出現離職同仁
    # （2026-08-10 owner 回報「不該出現 superuser」時已立此判準：
    #  在不在職由 is_active 表達，不另立系統帳號名單）。
    users = await user_repo.get_active_users(skip=0, limit=500)
    return {
        "success": True,
        "items": [
            {
                "id": u.id,
                "full_name": u.full_name,
                "username": u.username,
                "email": u.email,
                "is_active": u.is_active,
                "canonical_user_id": getattr(u, "canonical_user_id", None),
            }
            for u in users
        ],
        "total": len(users),
    }


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
            position=user.position,
            # 讓消費端分得出分身帳號（ADR-0025）—— 見 schema 註解
            canonical_user_id=getattr(user, "canonical_user_id", None),
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
# 部門選項 API
# ============================================================================

@router.post(
    "/departments",
    response_model=list[str],
    summary="取得部門選項列表",
    description="從使用者資料中動態取得所有不重複的部門名稱"
)
async def get_departments(
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(require_admin())
):
    """取得所有已使用的部門名稱（DB 驅動，無硬編碼）"""
    return await user_repo.get_distinct_departments()


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

    # 超級管理員保護（2026-08-10 修正語意）
    #
    # 原本是**絕對禁止**：只要對象是超管就擋，不管操作者是誰、也不管系統裡
    # 還有沒有其他超管。於是 owner（本身也是超管）無法維護那個 2025-12-28
    # 就停用的種子帳號 admin@example.com —— 一個永遠刪不掉的帳號。
    #
    # 這道守衛的用意是「不要把所有人鎖在門外」，不是「超管永生」。
    # 改為：只擋「刪掉最後一個可用的超管」與「刪掉自己」。
    if is_superuser_user(user):
        if user.id == current_user.id:
            raise ForbiddenException(message="不可刪除自己的帳號")
        if not await _has_other_active_superuser(user_repo, exclude_id=user.id):
            raise ForbiddenException(
                message="這是系統中最後一個可用的超級管理員，刪除後將無人能管理系統"
            )

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

    # 超級管理員保護 —— 同刪除，只擋「最後一個」與「自己」（見上方說明）
    if is_superuser_user(user) and not status_data.is_active:
        if user.id == current_user.id:
            raise ForbiddenException(message="不可停用自己的帳號")
        if not await _has_other_active_superuser(user_repo, exclude_id=user.id):
            raise ForbiddenException(
                message="這是系統中最後一個可用的超級管理員，停用後將無人能管理系統"
            )

    user.is_active = status_data.is_active
    user.updated_at = datetime.now()

    await user_repo.db.commit()
    await user_repo.db.refresh(user)

    return user
