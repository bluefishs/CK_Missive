"""
使用者管理與權限管理 API 端點
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
import json

from app.db.database import get_async_db
from app.core.auth_service import AuthService
from app.api.endpoints.auth import get_current_user
from app.schemas.auth import (
    UserResponse, UserUpdate, UserListResponse, UserSearchParams,
    UserPermissions, PermissionCheck, UserSessionsResponse, UserRegister
)
from app.extended.models import User, UserSession

router = APIRouter()

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """需要管理員權限的依賴函數"""
    if not AuthService.check_admin_permission(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    return current_user

# === 使用者管理 ===

@router.get("/users", response_model=UserListResponse, summary="取得使用者列表")
async def get_users(
    params: UserSearchParams = Depends(),
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """
    取得使用者列表 (管理員功能)
    - 支援搜尋、篩選與分頁
    """
    query = select(User).where(User.is_active == True)
    
    # 搜尋條件
    if params.q:
        search_term = f"%{params.q}%"
        query = query.where(
            (User.email.ilike(search_term)) |
            (User.username.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )
    
    # 篩選條件
    if params.role:
        query = query.where(User.role == params.role)
    
    if params.auth_provider:
        query = query.where(User.auth_provider == params.auth_provider)
    
    if params.is_active is not None:
        query = query.where(User.is_active == params.is_active)
    
    # 計算總數
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分頁
    offset = (params.page - 1) * params.per_page
    query = query.offset(offset).limit(params.per_page)
    
    # 執行查詢
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        users=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=params.page,
        per_page=params.per_page
    )

@router.post("/users", response_model=UserResponse, summary="新增使用者")
async def create_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """新增使用者 (管理員功能)"""
    # 檢查 email 唯一性
    existing_email = await AuthService.get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該電子郵件已被使用"
        )
    
    # 檢查 username 唯一性
    existing_username = await AuthService.get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該使用者名稱已被使用"
        )
    
    # 建立新使用者
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
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return UserResponse.model_validate(new_user)

@router.get("/users/{user_id}", response_model=UserResponse, summary="取得指定使用者")
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """取得指定使用者詳細資訊 (管理員功能)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )
    
    return UserResponse.model_validate(user)

@router.put("/users/{user_id}", response_model=UserResponse, summary="更新使用者資訊")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """更新使用者資訊 (管理員功能)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )
    
    # 更新欄位
    update_data = user_update.dict(exclude_unset=True)
    
    # 檢查 email 唯一性
    if "email" in update_data and update_data["email"] != user.email:
        existing_email = await AuthService.get_user_by_email(db, update_data["email"])
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="該電子郵件已被使用"
            )
    
    # 檢查 username 唯一性
    if "username" in update_data and update_data["username"] != user.username:
        existing_username = await AuthService.get_user_by_username(db, update_data["username"])
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="該使用者名稱已被使用"
            )
    
    # 執行更新
    await db.execute(
        update(User).where(User.id == user_id).values(**update_data)
    )
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)

@router.delete("/users/{user_id}", summary="刪除使用者")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """軟刪除使用者 (管理員功能)"""
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無法刪除自己的帳號"
        )
    
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
    )
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )
    
    await db.commit()
    return {"message": "使用者已刪除"}

# === 權限管理 ===

@router.get("/users/{user_id}/permissions", response_model=UserPermissions, summary="取得使用者權限")
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """取得指定使用者的權限列表 (管理員功能)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
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

@router.put("/users/{user_id}/permissions", response_model=UserPermissions, summary="更新使用者權限")
async def update_user_permissions(
    user_id: int,
    permissions_data: UserPermissions,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """更新指定使用者的權限 (管理員功能)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者不存在"
        )
    
    # 更新權限
    permissions_json = json.dumps(permissions_data.permissions)
    
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            permissions=permissions_json,
            role=permissions_data.role
        )
    )
    await db.commit()
    
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

@router.get("/users/{user_id}/sessions", response_model=UserSessionsResponse, summary="取得使用者會話")
async def get_user_sessions(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """取得指定使用者的所有會話 (管理員功能)"""
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .order_by(UserSession.created_at.desc())
    )
    sessions = result.scalars().all()
    
    # 假設當前會話是最新的活躍會話
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

@router.delete("/sessions/{session_id}", summary="撤銷會話")
async def revoke_user_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """撤銷指定會話 (管理員功能)"""
    result = await db.execute(select(UserSession).where(UserSession.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="會話不存在"
        )
    
    success = await AuthService.revoke_session(db, session.token_jti)
    
    if success:
        return {"message": "會話已撤銷"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="撤銷會話失敗"
        )

# === 權限預設清單 ===

@router.get("/permissions/available", summary="取得可用權限列表")
async def get_available_permissions(
    admin_user: User = Depends(require_admin)
):
    """取得系統中所有可用的權限列表 (管理員功能)"""
    return {
        "permissions": [
            # 公文管理權限
            "documents:read",
            "documents:create", 
            "documents:edit",
            "documents:delete",
            "documents:export",
            
            # 承攬案件權限
            "projects:read",
            "projects:create",
            "projects:edit", 
            "projects:delete",
            
            # 機關單位權限
            "agencies:read",
            "agencies:create",
            "agencies:edit",
            "agencies:delete",
            
            # 廠商管理權限
            "vendors:read",
            "vendors:create",
            "vendors:edit",
            "vendors:delete",
            
            # 系統管理權限
            "admin:users",
            "admin:settings",
            "admin:database",
            "admin:site_management",
            
            # 報表權限
            "reports:view",
            "reports:export",
            
            # 其他功能權限
            "calendar:read",
            "calendar:edit",
            "notifications:read"
        ],
        "roles": [
            {
                "name": "unverified",
                "display_name": "未驗證者",
                "default_permissions": []
            },
            {
                "name": "user",
                "display_name": "一般使用者",
                "default_permissions": [
                    "documents:read",
                    "projects:read", 
                    "agencies:read",
                    "vendors:read",
                    "calendar:read",
                    "reports:view"
                ]
            },
            {
                "name": "admin", 
                "display_name": "管理員",
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
            {
                "name": "superuser",
                "display_name": "超級管理員", 
                "default_permissions": ["*"]  # 所有權限
            }
        ]
    }