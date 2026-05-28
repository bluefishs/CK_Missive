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

from .common import get_current_user, get_superuser_mock, is_internal_ip

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

    A+B 雙模式（5/04 owner 確認）：
    - 內網（192.168.x / 10.x / 172.16-31.x / 127.x）+ AUTH_DISABLED → mock superuser
    - 公網（CF Tunnel x-forwarded-for / cf-connecting-ip）→ 認 cookie 或 header 真認證
    """
    # 縱深防禦（commit 4ac57f55 同邏輯）：CF 公網一律不走 mock
    is_public_request = bool(
        request.headers.get("cf-connecting-ip") or request.headers.get("cf-ray")
    )

    ip_address = request.client.host if request.client else None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()

    if settings.AUTH_DISABLED and not is_public_request and is_internal_ip(ip_address):
        logger.info(
            f"[AUTH] /me Internal/Dev access - IP: {ip_address}"
        )
        return UserProfile.model_validate(get_superuser_mock())

    # 真實認證：優先 Authorization header，再 fallback 到 access_token cookie
    token = None
    if credentials is not None:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("access_token")

    # L49.17 (2026-05-28) 內網信任網路 token-less fallback（與 common.get_current_user 對齊）：
    # 內網 production（AUTH_DISABLED=false）+ 無 token + 非 CF Tunnel → mock superuser
    # 配合 EntryPage L49.15.1 「快速進入」避免 dashboard 401 死循環
    if not token and not is_public_request and is_internal_ip(ip_address):
        logger.info(
            "[AUTH] /me Internal trusted-network fallback - IP: %s", ip_address,
        )
        return UserProfile.model_validate(get_superuser_mock())

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await AuthService.get_current_user_from_token(db, token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證憑證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserProfile.model_validate(user)


# 2026-05-25 補：ADR-0046 Public Auth Endpoint Contract — /profile 與 /me 對齊
@router.post("/profile", response_model=UserProfile, summary="取得當前使用者 profile（ADR-0046 對齊）")
@limiter.limit("30/minute")
async def get_current_user_profile_v2(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """ADR-0046 endpoint contract — /profile 為 /me 同義 endpoint"""
    return await get_current_user_info(request, response, credentials, db)


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
            detail="更新個人資料失敗，請稍後再試"
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
            detail="修改密碼失敗，請稍後再試"
        )
