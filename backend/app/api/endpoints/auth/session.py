"""
認證模組 - 會話管理端點

包含: /refresh, /logout, /check

v3.1.0 - 2026-02-07
- refresh 成功後設定 httpOnly cookies
- logout 時清除認證 cookies
- refresh 支援從 cookie 讀取 refresh_token（向後相容）
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response, JSONResponse

from app.db.database import get_async_db
from app.core.auth_service import AuthService, security
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.schemas.auth import TokenResponse, RefreshTokenRequest
from app.extended.models import User
from app.services.audit_service import AuditService

from .common import get_client_info, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    refresh_request: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """
    刷新存取令牌

    支援兩種方式提供 refresh_token（向後相容）：
    1. JSON body: {"refresh_token": "xxx"} （傳統方式）
    2. httpOnly cookie: refresh_token （新安全方式）

    優先使用 body 中的 refresh_token，若無則從 cookie 讀取。
    """
    # 取得 refresh token：優先使用 body，否則從 cookie 讀取
    token_value = None
    if refresh_request and refresh_request.refresh_token:
        token_value = refresh_request.refresh_token
    else:
        token_value = request.cookies.get("refresh_token")

    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await AuthService.verify_refresh_token(db, token_value)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效或過期的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    ip_address, user_agent = get_client_info(request)

    token_response = await AuthService.generate_login_response(
        db, user, ip_address, user_agent, is_refresh=True
    )

    # 建立 JSONResponse 以便同時設定 cookies
    response = JSONResponse(
        content=token_response.model_dump(mode="json"),
    )

    # 設定新的 httpOnly cookies
    AuthService.set_auth_cookies(response, token_response)

    return response


@router.post("/logout", summary="使用者登出")
async def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """
    使用者登出 - 撤銷當前會話並清除認證 cookies

    Token 取得優先順序（向後相容）：
    1. Authorization header (Bearer token)
    2. access_token cookie (httpOnly)
    """
    if settings.AUTH_DISABLED:
        logger.info("[AUTH] 開發模式 - 登出請求（無需驗證）")
        response = JSONResponse(content={"message": "登出成功（開發模式）"})
        AuthService.clear_auth_cookies(response)
        return response

    # 嘗試從 Authorization header 或 cookie 取得 token
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        logger.info("[AUTH] 登出請求（無 token）")
        response = JSONResponse(content={"message": "登出成功"})
        AuthService.clear_auth_cookies(response)
        return response

    payload = AuthService.verify_token(token)

    if not payload:
        logger.info("[AUTH] 登出請求（token 無效或已過期）")
        response = JSONResponse(content={"message": "登出成功"})
        AuthService.clear_auth_cookies(response)
        return response

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

    # 清除認證 cookies
    response = JSONResponse(content={"message": "登出成功"})
    AuthService.clear_auth_cookies(response)
    return response


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
