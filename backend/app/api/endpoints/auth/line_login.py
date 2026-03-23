"""
認證模組 - LINE Login OAuth 端點

包含: /line/callback, /line/bind, /line/unbind

v1.0.0 - 2026-03-22
- LINE Login OAuth 2.1 callback (code → token → profile)
- 已登入帳號綁定/解除 LINE
- 共用 AuthService.generate_login_response() 簽發 JWT
"""

import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.rate_limiter import limiter
from app.db.database import get_async_db
from app.core.auth_service import AuthService
from app.core.config import settings
from app.schemas.auth import (
    LineAuthRequest,
    LineBindRequest,
    LineUserInfo,
    TokenResponse,
)
from app.extended.models import User
from app.services.audit_service import AuditService

from .common import get_current_user, get_client_info

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/line", tags=["LINE Login"])


# ============================================================================
# LINE OAuth Helper
# ============================================================================

async def _exchange_line_token(code: str, redirect_uri: Optional[str] = None) -> dict:
    """
    LINE OAuth 2.1: authorization code → access_token + id_token

    https://developers.line.biz/en/docs/line-login/integrate-line-login/#get-access-token
    """
    channel_id = getattr(settings, "LINE_LOGIN_CHANNEL_ID", None) or ""
    channel_secret = getattr(settings, "LINE_LOGIN_CHANNEL_SECRET", None) or ""

    if not channel_id or not channel_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LINE Login 尚未設定 (LINE_LOGIN_CHANNEL_ID / LINE_LOGIN_CHANNEL_SECRET)",
        )

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or getattr(settings, "LINE_LOGIN_REDIRECT_URI", ""),
        "client_id": channel_id,
        "client_secret": channel_secret,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post("https://api.line.me/oauth2/v2.1/token", data=payload)
        if resp.status_code != 200:
            logger.error(f"[LINE] Token exchange failed: {resp.status_code} {resp.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LINE 授權碼無效或已過期，請重新登入",
            )
        return resp.json()


async def _get_line_profile(access_token: str, id_token: Optional[str] = None) -> LineUserInfo:
    """
    LINE Profile API: 取得使用者基本資料 + id_token 解碼 email

    https://developers.line.biz/en/docs/line-login/getting-user-profile/
    https://developers.line.biz/en/docs/line-login/verify-id-token/
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.line.me/v2/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            logger.error(f"[LINE] Profile fetch failed: {resp.status_code}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LINE access token 無效",
            )
        data = resp.json()

        # 從 id_token 解碼 email (LINE Verify API)
        email = None
        if id_token:
            channel_id = getattr(settings, "LINE_LOGIN_CHANNEL_ID", None) or ""
            try:
                verify_resp = await client.post(
                    "https://api.line.me/oauth2/v2.1/verify",
                    data={"id_token": id_token, "client_id": channel_id},
                )
                if verify_resp.status_code == 200:
                    verify_data = verify_resp.json()
                    email = verify_data.get("email")
                    if email:
                        logger.info(f"[LINE] id_token 取得 email: {email}")
                else:
                    logger.warning(f"[LINE] id_token verify failed: {verify_resp.status_code}")
            except Exception as e:
                logger.warning(f"[LINE] id_token 解碼失敗: {e}")

        return LineUserInfo(
            line_user_id=data["userId"],
            display_name=data["displayName"],
            picture_url=data.get("pictureUrl"),
            email=email,
        )


async def _get_user_by_line_id(db: AsyncSession, line_user_id: str) -> Optional[User]:
    """透過 LINE User ID 查找使用者"""
    result = await db.execute(
        select(User).where(User.line_user_id == line_user_id)
    )
    return result.scalars().first()


# ============================================================================
# API 端點
# ============================================================================

@router.post("/callback", response_model=TokenResponse, summary="LINE Login OAuth Callback")
@limiter.limit("10/minute")
async def line_login_callback(
    request: Request,
    line_request: LineAuthRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    LINE Login OAuth 2.1 callback

    流程:
    1. authorization code → access_token (LINE API)
    2. access_token → user profile (LINE API)
    3. 查找/建立使用者 (line_user_id match → email match → create)
    4. 檢查帳號狀態
    5. 簽發 JWT + httpOnly cookie
    """
    ip_address, user_agent = get_client_info(request)

    try:
        # 1. Exchange code for token
        token_data = await _exchange_line_token(line_request.code, line_request.redirect_uri)
        access_token = token_data["access_token"]
        id_token = token_data.get("id_token")

        # 2. Get LINE profile (含 id_token email 解碼)
        line_info = await _get_line_profile(access_token, id_token)
        logger.info(f"[LINE] 登入嘗試: {line_info.display_name} ({line_info.line_user_id[:8]}...)")

        # 3. Find user (line_user_id → email → reject)
        # 不再自動建立 placeholder 帳號，避免帳號碎片化
        user = await _get_user_by_line_id(db, line_info.line_user_id)

        if user:
            # 已綁定的使用者 — 更新顯示名稱
            user.line_display_name = line_info.display_name
            if line_info.picture_url:
                user.avatar_url = line_info.picture_url
            user.last_login = datetime.utcnow()
            await db.commit()
            await db.refresh(user)
            logger.info(f"[LINE] 已綁定使用者登入: {user.email} (ID: {user.id})")
        else:
            # 嘗試以 email 配對 (LINE 不一定提供 email)
            if line_info.email:
                existing_user = await AuthService.get_user_by_email(db, line_info.email)
                if existing_user:
                    # 檢查 line_user_id 是否已被其他帳號佔用 (unique 防護)
                    duplicate = await _get_user_by_line_id(db, line_info.line_user_id)
                    if duplicate and duplicate.id != existing_user.id:
                        logger.error(f"[LINE] line_user_id 衝突: {line_info.line_user_id} 已綁定到 user {duplicate.id}")
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="此 LINE 帳號已綁定到其他使用者，請聯繫管理員處理。",
                        )
                    # 自動綁定 LINE 到 email 匹配的現有帳號
                    existing_user.line_user_id = line_info.line_user_id
                    existing_user.line_display_name = line_info.display_name
                    if line_info.picture_url:
                        existing_user.avatar_url = line_info.picture_url
                    existing_user.last_login = datetime.utcnow()
                    await db.commit()
                    await db.refresh(existing_user)
                    user = existing_user
                    logger.info(f"[LINE] 現有帳號自動綁定 LINE: {user.email} (ID: {user.id})")
                    # 記錄自動綁定事件
                    await AuditService.log_auth_event(
                        event_type="LINE_AUTO_BIND",
                        user_id=user.id,
                        email=user.email,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        details={
                            "line_user_id": line_info.line_user_id,
                            "line_display_name": line_info.display_name,
                            "match_method": "email",
                        },
                        success=True,
                    )

            if not user:
                # 無匹配帳號 — 拒絕登入，引導至綁定流程
                logger.info(f"[LINE] 未綁定帳號，拒絕建立: {line_info.display_name} ({line_info.line_user_id[:8]}...)")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"LINE 帳號「{line_info.display_name}」尚未綁定系統帳號。"
                        "請先使用 Email 或 Google 登入後，在個人資料頁面綁定 LINE，"
                        "或請管理員在後台為您綁定。"
                    ),
                )

        # 4. Check account status
        if not user.is_active:
            await AuditService.log_auth_event(
                event_type="LOGIN_BLOCKED",
                user_id=user.id,
                email=user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "account_deactivated", "auth_provider": "line"},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您的帳戶已被停用，無法登入系統。",
            )

        # 5. MFA check
        if user.mfa_enabled and user.mfa_secret:
            from .oauth import _create_mfa_token
            mfa_token = _create_mfa_token(user)
            return JSONResponse(
                content={"mfa_required": True, "mfa_token": mfa_token, "message": "請輸入雙因素認證驗證碼"},
            )

        # 6. Generate login response
        token_response = await AuthService.generate_login_response(db, user, ip_address, user_agent)

        await AuditService.log_auth_event(
            event_type="LOGIN_SUCCESS",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"auth_provider": "line"},
            success=True,
        )

        response = JSONResponse(content=token_response.model_dump(mode="json"))
        AuthService.set_auth_cookies(response, token_response)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LINE] 登入失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LINE 登入失敗，請稍後再試",
        )


@router.post("/bind", summary="綁定 LINE 帳號")
@limiter.limit("5/minute")
async def bind_line_account(
    request: Request,
    bind_request: LineBindRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    已登入使用者綁定 LINE 帳號

    🔒 需要認證
    """
    if current_user.line_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="此帳號已綁定 LINE，請先解除綁定",
        )

    try:
        token_data = await _exchange_line_token(bind_request.code, bind_request.redirect_uri)
        line_info = await _get_line_profile(token_data["access_token"])

        # 檢查 LINE ID 是否已被其他帳號綁定
        existing = await _get_user_by_line_id(db, line_info.line_user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="此 LINE 帳號已綁定到其他使用者",
            )

        current_user.line_user_id = line_info.line_user_id
        current_user.line_display_name = line_info.display_name
        if line_info.picture_url:
            current_user.avatar_url = line_info.picture_url
        await db.commit()

        logger.info(f"[LINE] 帳號綁定成功: {current_user.email} ↔ {line_info.display_name}")
        return {"success": True, "message": f"已成功綁定 LINE 帳號: {line_info.display_name}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LINE] 綁定失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LINE 帳號綁定失敗",
        )


@router.post("/unbind", summary="解除 LINE 綁定")
async def unbind_line_account(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    解除當前帳號的 LINE 綁定

    🔒 需要認證
    注意: 若帳號是純 LINE 建立且無密碼，解除後將無法登入
    """
    if not current_user.line_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此帳號尚未綁定 LINE",
        )

    # 安全檢查：純 LINE 帳號且無其他登入方式
    has_password = bool(current_user.password_hash)
    has_google = bool(current_user.google_id)
    if not has_password and not has_google:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此帳號僅有 LINE 登入方式，解除綁定後將無法登入。請先設定密碼或綁定 Google 帳號。",
        )

    old_name = current_user.line_display_name
    current_user.line_user_id = None
    current_user.line_display_name = None
    await db.commit()

    logger.info(f"[LINE] 解除綁定: {current_user.email} (原 LINE: {old_name})")
    return {"success": True, "message": "已解除 LINE 帳號綁定"}
