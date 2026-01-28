"""
認證模組 - 會話管理端點

包含: /refresh, /logout, /check
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.core.auth_service import AuthService, security
from app.core.config import settings
from app.schemas.auth import TokenResponse, RefreshTokenRequest
from app.extended.models import User
from app.services.audit_service import AuditService

from .common import get_client_info, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    刷新存取令牌
    - **refresh_token**: 刷新令牌
    """
    user = await AuthService.verify_refresh_token(db, refresh_request.refresh_token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效或過期的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    ip_address, user_agent = get_client_info(request)

    return await AuthService.generate_login_response(db, user, ip_address, user_agent)


@router.post("/logout", summary="使用者登出")
async def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """使用者登出 - 撤銷當前會話"""
    if settings.AUTH_DISABLED:
        logger.info("[AUTH] 開發模式 - 登出請求（無需驗證）")
        return {"message": "登出成功（開發模式）"}

    if not credentials or not credentials.credentials:
        logger.info("[AUTH] 登出請求（無 token）")
        return {"message": "登出成功"}

    token = credentials.credentials
    payload = AuthService.verify_token(token)

    if not payload:
        logger.info("[AUTH] 登出請求（token 無效或已過期）")
        return {"message": "登出成功"}

    jti = payload.get("jti")
    user_id = payload.get("sub")
    email = payload.get("email")
    ip_address, user_agent = get_client_info(request)

    if jti:
        await AuthService.revoke_session(db, jti)

    await AuditService.log_auth_event(
        event_type="LOGOUT",
        user_id=int(user_id) if user_id else None,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"session_jti": jti},
        success=True,
    )

    logger.info(f"[AUTH] 使用者登出: {email}")
    return {"message": "登出成功"}


@router.post("/check", summary="檢查認證狀態")
async def check_auth_status(current_user: User = Depends(get_current_user)):
    """檢查當前認證狀態 (POST-only 安全模式)"""
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "auth_provider": current_user.auth_provider,
        "is_admin": current_user.is_admin,
    }
