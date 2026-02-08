"""
認證模組 - OAuth 與登入端點

包含: /login, /google, /register

v3.2.0 - 2026-02-08
- 新增 MFA 雙因素認證支援
- 登入成功後檢查 MFA 狀態，若啟用則返回 mfa_required + mfa_token
- 登入成功後設定 httpOnly cookie（同時保留 JSON body 向後相容）
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response, JSONResponse

from app.core.rate_limiter import limiter

from app.db.database import get_async_db
from app.core.auth_service import AuthService, ALGORITHM
from app.core.config import settings
from app.core.mfa_service import MFA_TOKEN_EXPIRE_SECONDS
from app.schemas.auth import (
    UserRegister,
    GoogleAuthRequest,
    TokenResponse,
    UserResponse,
)
from app.extended.models import User
from app.services.audit_service import AuditService

from .common import get_client_info

logger = logging.getLogger(__name__)
router = APIRouter()


def _create_mfa_token(user: User) -> str:
    """
    建立 MFA 臨時 token

    此 token 僅用於 MFA 驗證流程，不是完整的 access_token。
    有效期為 5 分鐘。
    """
    expire = datetime.utcnow() + timedelta(seconds=MFA_TOKEN_EXPIRE_SECONDS)
    payload = {
        "sub": str(user.id),
        "type": "mfa_pending",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login", response_model=TokenResponse, summary="帳號密碼登入")
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    """
    使用者帳號密碼登入（內網環境主要認證方式）

    - **username**: 使用者名稱或信箱
    - **password**: 密碼

    適用場景:
    - 內網環境（無法使用 Google OAuth）
    - 本地開發測試
    - 備用認證方式

    回應:
    - JSON body 包含 token 資訊（向後相容）
    - 同時設定 httpOnly cookies（新安全機制）
    """
    masked_user = form_data.username[:2] + "***" if len(form_data.username) > 2 else "***"
    logger.info(f"[AUTH] 帳密登入嘗試: {masked_user}")
    try:
        user = await AuthService.authenticate_user(
            db, form_data.username, form_data.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳號或密碼錯誤",
                headers={"WWW-Authenticate": "Bearer"},
            )

        ip_address, user_agent = get_client_info(request)

        # 檢查 MFA 狀態
        if user.mfa_enabled and user.mfa_secret:
            mfa_token = _create_mfa_token(user)
            logger.info(f"[AUTH] 使用者 {user.id} 需要 MFA 驗證")
            return JSONResponse(
                content={
                    "mfa_required": True,
                    "mfa_token": mfa_token,
                    "message": "請輸入雙因素認證驗證碼",
                },
            )

        token_response = await AuthService.generate_login_response(
            db, user, ip_address, user_agent
        )

        # 建立 JSONResponse 以便同時設定 cookies
        response = JSONResponse(
            content=token_response.model_dump(mode="json"),
        )

        # 設定 httpOnly cookies（新安全機制）
        AuthService.set_auth_cookies(response, token_response)

        return response

    except HTTPException as http_exc:
        # 帳號鎖定 (423) 時，返回包含剩餘時間的 JSON 回應
        if http_exc.status_code == 423:
            locked_until = http_exc.headers.get("X-Locked-Until") if http_exc.headers else None
            remaining_minutes = http_exc.headers.get("X-Remaining-Minutes") if http_exc.headers else None
            return JSONResponse(
                status_code=423,
                content={
                    "detail": http_exc.detail,
                    "locked_until": locked_until,
                    "remaining_minutes": int(remaining_minutes) if remaining_minutes else None,
                },
            )
        raise http_exc
    except Exception as e:
        logger.error(f"[AUTH] 登入服務內部錯誤: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登入服務內部錯誤，請稍後再試或聯繫管理員",
        )


@router.post("/google", response_model=TokenResponse, summary="Google OAuth 登入")
@limiter.limit("10/minute")
async def google_oauth_login(
    request: Request,
    response: Response,
    google_request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Google OAuth 第三方登入 (主要認證方式)

    - **credential**: Google OAuth ID Token

    流程:
    1. 驗證 Google Token
    2. 檢查網域白名單
    3. 查找/建立使用者
    4. 檢查帳號狀態
    5. 生成 JWT Token
    """
    ip_address, user_agent = get_client_info(request)

    try:
        # 1. 驗證 Google Token
        google_info = await AuthService.verify_google_token(google_request.credential)
        logger.info(f"[AUTH] Google 登入嘗試: {google_info.email}")

        # 2. 檢查網域白名單
        if not AuthService.check_email_domain(google_info.email):
            logger.warning(f"[AUTH] 網域被拒: {google_info.email}")
            await AuditService.log_auth_event(
                event_type="LOGIN_BLOCKED",
                email=google_info.email,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "domain_not_allowed"},
                success=False,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您的 Google 帳號網域不在允許清單內，無法登入系統。請聯絡管理者。",
            )

        # 3. 嘗試找尋現有使用者
        user = await AuthService.get_user_by_google_id(db, google_info.google_id)
        is_new_user = False

        if user:
            user.avatar_url = google_info.avatar_url
            user.email_verified = google_info.email_verified
            user.last_login = datetime.utcnow()
            await db.commit()
            await db.refresh(user)
            logger.info(f"[AUTH] 現有使用者登入: {user.email} (ID: {user.id})")
        else:
            existing_user = await AuthService.get_user_by_email(db, google_info.email)

            if existing_user:
                existing_user.google_id = google_info.google_id
                existing_user.avatar_url = google_info.avatar_url
                existing_user.auth_provider = "google"
                existing_user.email_verified = google_info.email_verified
                existing_user.last_login = datetime.utcnow()
                await db.commit()
                await db.refresh(existing_user)
                user = existing_user
                logger.info(f"[AUTH] 現有帳號綁定 Google: {user.email}")
            else:
                is_new_user = True
                user = await AuthService.create_oauth_user(db, google_info)

                user.role = AuthService.get_default_user_role()
                user.is_active = AuthService.should_auto_activate()
                user.permissions = AuthService.get_default_permissions()

                await db.commit()
                await db.refresh(user)
                logger.info(
                    f"[AUTH] 新使用者建立: {user.email} "
                    f"(is_active={user.is_active}, role={user.role})"
                )

                await AuditService.log_auth_event(
                    event_type="ACCOUNT_CREATED",
                    user_id=user.id,
                    email=user.email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "auto_activated": user.is_active,
                        "default_role": user.role,
                    },
                    success=True,
                )

        # 4. 檢查帳號狀態
        if not user.is_active:
            await AuditService.log_auth_event(
                event_type="LOGIN_BLOCKED",
                user_id=user.id,
                email=user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "reason": "pending_approval"
                    if is_new_user
                    else "account_deactivated"
                },
                success=False,
            )

            if is_new_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您的帳號已建立，但需要管理員審核後才能使用。請聯絡管理者啟用您的帳號。",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您的帳戶已被停用，無法登入系統。如有疑問請聯絡管理者。",
                )

        # 5. 檢查 MFA 狀態
        if user.mfa_enabled and user.mfa_secret:
            mfa_token = _create_mfa_token(user)
            logger.info(f"[AUTH] Google 使用者 {user.id} 需要 MFA 驗證")
            return JSONResponse(
                content={
                    "mfa_required": True,
                    "mfa_token": mfa_token,
                    "message": "請輸入雙因素認證驗證碼",
                },
            )

        # 6. 生成登入回應
        token_response = await AuthService.generate_login_response(
            db, user, ip_address, user_agent
        )

        await AuditService.log_auth_event(
            event_type="LOGIN_SUCCESS",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"auth_provider": "google"},
            success=True,
        )

        logger.info(f"[AUTH] 登入成功: {user.email}")

        # 建立 JSONResponse 以便同時設定 cookies
        response = JSONResponse(
            content=token_response.model_dump(mode="json"),
        )

        # 設定 httpOnly cookies（新安全機制）
        AuthService.set_auth_cookies(response, token_response)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Google 登入失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google 登入失敗，請稍後再試或聯繫管理員",
        )


@router.post(
    "/register",
    response_model=UserResponse,
    summary="使用者註冊 (已棄用)",
    deprecated=True,
    tags=["deprecated"],
)
async def register_user(
    user_data: UserRegister, db: AsyncSession = Depends(get_async_db)
):
    """
    ⚠️ **已棄用** - 請使用 Google OAuth 登入 (/auth/google) 自動建立帳號

    使用者註冊
    - **email**: 電子郵件
    - **username**: 使用者名稱
    - **full_name**: 完整姓名
    - **password**: 密碼

    注意: 此端點將在未來版本移除。新使用者請直接使用 Google 帳號登入，系統將自動建立帳號。
    """
    logger.warning(f"[AUTH] 使用已棄用的註冊端點: {user_data.email}")
    existing_user = await AuthService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="該電子郵件已被註冊"
        )

    existing_username = await AuthService.get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="該使用者名稱已被使用"
        )

    password_hash = AuthService.get_password_hash(user_data.password)

    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        password_hash=password_hash,
        auth_provider="email",
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)
