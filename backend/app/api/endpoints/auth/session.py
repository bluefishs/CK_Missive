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
from starlette.responses import JSONResponse

from app.db.database import get_async_db
from app.core.auth_service import AuthService, security
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.schemas.auth import TokenResponse, RefreshTokenRequest
from app.extended.models import User
from app.services.audit import AuditService

from .common import get_client_info, get_current_user
from .sso_bridge import try_mint_session_from_sso_cookie

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

    user = await AuthService.verify_refresh_token(db, token_value) if token_value else None

    if user:
        ip_address, user_agent = get_client_info(request)
        token_response = await AuthService.generate_login_response(
            db, user, ip_address, user_agent, is_refresh=True
        )
    else:
        # I7 無痛續命（L80）：refresh_token 缺失/失效，但帶有效 ck_employee SSO cookie →
        # 就地重鑄 SSO session（等同 sso-bridge，8h）。前端既有「refresh 成功→重試原請求」
        # 線路即可透明復原，無整頁 reload、無存檔白填。SSO 過期後 refresh 恆走此路（其
        # refresh_token 隨 8h session 一同失效）。非 SSO 或無有效 cookie → 維持原 401。
        token_response = await try_mint_session_from_sso_cookie(request, db)
        if token_response is None:
            # 走到這裡＝**已經確定沒救了**：refresh_token 失效，且沒有可用的 SSO cookie
            # 可以重鑄。這與「暫時性 401」是完全不同的兩件事，但兩者長得一樣。
            #
            # 2026-08-07 owner 實測：08:49 SSO 登入 → ck_employee 8h → 16:49 到期；
            # 16:39 的 refresh 仍成功並發出一張**到 17:39** 的 session（憑證只剩 10 分鐘
            # 卻發了 60 分鐘的通行證）；17:39 到期後 refresh 走到這一行 → 401。
            # 前端有一道守衛（L74/I-series）：相信自己已登入時，單次 401 不清 session、
            # 不跳登入頁，只讓該請求失敗 —— 那是為了擋「閃回登入頁」的反覆回歸，對暫時性
            # 401 正確。但這裡是**永久失效**，守衛於是把它變成無止盡的靜默失敗：owner 的
            # 刪除動作直接消失（紀錄 391 仍在），且會一直點一直失敗到手動重整為止。
            #
            # 修法遵循 L74 的原則 —— **明確事件優先於被動檢查**：由伺服器明講「這條路
            # 已經死了、必須重新登入」，前端才有依據推翻自己的樂觀假設。用 response
            # header 而非改 detail 形狀，對既有呼叫端零影響。
            headers = {"WWW-Authenticate": "Bearer"}
            if token_value:
                # 只有「**曾經**有憑證、現在確定死了」才宣告必須重登。
                #
                # 完全沒帶 refresh_token 的請求（匿名首載、bootstrap 進行中）刻意**不**加
                # 這個 header —— 那正是「閃回登入頁」反覆回歸的觸發路徑，必須繼續留在
                # 前端守衛的保守行為底下。收窄條件比訊號本身更重要。
                headers["X-Reauth-Required"] = "1"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="登入階段已到期，請重新登入" if token_value else "未提供刷新令牌",
                headers=headers,
            )

    # 建立 JSONResponse 以便同時設定 cookies
    response = JSONResponse(
        content=token_response.model_dump(mode="json"),
    )

    # 設定新的 httpOnly cookies — A+B：以 request scheme 決定 Secure
    AuthService.set_auth_cookies(response, token_response, request=request)

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
async def check_auth_status(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """檢查當前認證狀態 (POST-only 安全模式)"""
    # 內網/開發模式存取記錄 — 每個 user+IP 每天最多記錄一次
    try:
        from app.core.redis_client import get_redis
        import time
        redis = await get_redis()
        if redis:
            from .common import _get_real_ip
            ip = _get_real_ip(request) or "unknown"
            dedup_key = f"auth:access_log:{current_user.id}:{ip}:{time.strftime('%Y%m%d')}"
            already_logged = await redis.get(dedup_key)
            if not already_logged:
                await redis.setex(dedup_key, 86400, "1")
                from app.services.audit import AuditService
                ua = request.headers.get("user-agent", "")[:200]
                await AuditService.log_auth_event(
                    event_type="LOGIN_SUCCESS",
                    user_id=current_user.id,
                    email=current_user.email,
                    ip_address=ip,
                    user_agent=ua,
                    details={"auth_provider": current_user.auth_provider or "quick_entry", "mode": "internal"},
                    success=True,
                )
    except Exception:
        pass  # 審計失敗不影響 auth check

    return {
        "authenticated": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "auth_provider": current_user.auth_provider,
        "is_admin": current_user.is_admin,
    }
