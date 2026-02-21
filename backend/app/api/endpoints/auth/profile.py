"""
認證模組 - 個人資料端點

包含: /me, /profile/update, /password/change

@version 2.0.0 - 使用 UserRepository 取代直接 ORM 查詢
@date 2026-02-06
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from starlette.responses import Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import limiter

from app.db.database import get_async_db
from app.core.auth_service import AuthService, security
from app.core.config import settings
from app.core.password_policy import validate_password
from app.schemas.auth import UserProfile, ProfileUpdate, PasswordChange
from app.extended.models import User
from app.repositories.user_repository import UserRepository

from .common import get_client_info, get_current_user, get_superuser_mock, is_internal_ip

logger = logging.getLogger(__name__)
router = APIRouter()


def get_user_repository(db: AsyncSession = Depends(get_async_db)) -> UserRepository:
    """取得 UserRepository 實例（工廠模式）"""
    return UserRepository(db)


@router.post("/me", response_model=UserProfile, summary="取得當前使用者資訊")
@limiter.limit("30/minute")
async def get_current_user_info(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得當前登入使用者的詳細資訊 (POST-only 安全模式)

    內網 IP 無需認證即可獲得超級管理員身份

    注意: 此端點委託給 AuthService 處理認證邏輯，
    保留 db 參數因為 AuthService 需要它。
    """
    ip_address = request.client.host if request.client else None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()

    is_development_localhost = (
        ip_address in ["127.0.0.1", "localhost"] and settings.DEVELOPMENT_MODE
    )

    if settings.AUTH_DISABLED and not is_development_localhost:
        logger.info(
            f"[AUTH] Internal/Dev access - IP: {ip_address}, AUTH_DISABLED: {settings.AUTH_DISABLED}"
        )
        return UserProfile.model_validate(get_superuser_mock())

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user = await AuthService.get_current_user_from_token(db, token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserProfile.model_validate(user)


@router.post("/profile/update", response_model=UserProfile, summary="更新個人資料")
@limiter.limit("10/minute")
async def update_profile(
    request: Request,
    response: Response,
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    更新當前使用者的個人資料

    - **username**: 使用者名稱（可選）
    - **full_name**: 完整姓名（可選）
    """
    logger.info(f"[AUTH] 更新個人資料: user_id={current_user.id}")

    try:
        user = await user_repo.get_by_id(current_user.id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="使用者不存在"
            )

        if profile_data.username and profile_data.username != user.username:
            if await user_repo.check_username_exists(
                profile_data.username, exclude_id=user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="該使用者名稱已被使用"
                )
            user.username = profile_data.username

        if profile_data.full_name is not None:
            user.full_name = profile_data.full_name

        if profile_data.department is not None:
            user.department = profile_data.department

        if profile_data.position is not None:
            user.position = profile_data.position

        await user_repo.db.commit()
        await user_repo.db.refresh(user)

        logger.info(f"[AUTH] 個人資料更新成功: user_id={user.id}")
        return UserProfile.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] 更新個人資料失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新個人資料失敗: {str(e)}"
        )


@router.post("/password/change", summary="修改密碼")
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    response: Response,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    修改當前使用者的密碼

    - **current_password**: 目前密碼
    - **new_password**: 新密碼（至少 6 個字元）

    注意：僅適用於 email 認證方式的使用者，Google OAuth 使用者無法修改密碼
    """
    logger.info(f"[AUTH] 修改密碼請求: user_id={current_user.id}")

    if current_user.auth_provider == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google 帳號使用者無法修改密碼，請透過 Google 管理您的密碼"
        )

    try:
        user = await user_repo.get_by_id(current_user.id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="使用者不存在"
            )

        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此帳號未設定密碼，無法修改"
            )

        if not AuthService.verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目前密碼不正確"
            )

        # 密碼策略驗證
        is_valid, message = validate_password(
            password_data.new_password,
            username=user.username
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        user.password_hash = AuthService.get_password_hash(password_data.new_password)
        await user_repo.db.commit()

        logger.info(f"[AUTH] 密碼修改成功: user_id={user.id}")
        return {"message": "密碼修改成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] 修改密碼失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改密碼失敗: {str(e)}"
        )
