"""
認證相關API端點

v2.3 - 2026-01-15
- 安全性改進: 將 PUT 端點改為 POST (POST-only 安全模式)
- POST /profile/update - 更新個人資料端點
- POST /password/change - 修改密碼端點

v2.2 - 2026-01-15
- 新增: 更新個人資料端點
- 新增: 修改密碼端點

v2.1 - 2026-01-12
- 支援雙認證方式: 傳統帳密登入 + Google OAuth
- 內網環境優先使用帳密登入
- 公網環境優先使用 Google OAuth
- 新增: 網域白名單檢查
- 新增: 新帳號審核機制
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional
import json

from app.db.database import get_async_db
from app.core.auth_service import AuthService, security
from app.schemas.auth import (
    UserRegister,
    GoogleAuthRequest,
    TokenResponse,
    UserResponse,
    UserProfile,
    RefreshTokenRequest,
    ProfileUpdate,
    PasswordChange,
)
from app.extended.models import User
from app.core.config import settings
from app.services.audit_service import AuditService
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter()


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """取得客戶端資訊"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.post("/login", response_model=TokenResponse, summary="帳號密碼登入")
async def login_for_access_token(
    request: Request,
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
    """
    logger.info(f"[AUTH] 帳密登入嘗試: {form_data.username}")
    try:
        # 驗證使用者
        user = await AuthService.authenticate_user(
            db, form_data.username, form_data.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳號或密碼錯誤",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 取得客戶端資訊
        ip_address, user_agent = get_client_info(request)

        # 生成登入回應
        return await AuthService.generate_login_response(
            db, user, ip_address, user_agent
        )

    except HTTPException as http_exc:
        # 如果是已知的 HTTP 錯誤 (例如 401)，直接重新拋出
        raise http_exc
    except Exception as e:
        # 捕捉所有其他未預期的錯誤 (例如資料庫連線失敗)
        # logger.error(f"登入時發生未預期錯誤: {e}", exc_info=True) # 建議加入日誌記錄
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入服務內部錯誤，請稍後再試或聯繫管理員。錯誤詳情: {str(e)}",
        )


@router.post("/google", response_model=TokenResponse, summary="Google OAuth 登入")
async def google_oauth_login(
    request: Request,
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
            # 記錄審計日誌
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
            # 更新現有使用者的資訊
            user.avatar_url = google_info.avatar_url
            user.email_verified = google_info.email_verified
            user.last_login = datetime.utcnow()
            await db.commit()
            await db.refresh(user)
            logger.info(f"[AUTH] 現有使用者登入: {user.email} (ID: {user.id})")
        else:
            # 檢查是否有相同 email 的使用者
            existing_user = await AuthService.get_user_by_email(db, google_info.email)

            if existing_user:
                # 更新現有使用者的 Google 資訊 (綁定 Google 帳號)
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
                # 建立新的 OAuth 使用者
                is_new_user = True
                user = await AuthService.create_oauth_user(db, google_info)

                # 根據設定決定是否自動啟用
                user.role = AuthService.get_default_user_role()
                user.is_active = AuthService.should_auto_activate()
                user.permissions = AuthService.get_default_permissions()

                await db.commit()
                await db.refresh(user)
                logger.info(
                    f"[AUTH] 新使用者建立: {user.email} "
                    f"(is_active={user.is_active}, role={user.role})"
                )

                # 記錄新帳號建立審計
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
            # 記錄審計日誌
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
                # 新帳號等待審核
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您的帳號已建立，但需要管理員審核後才能使用。請聯絡管理者啟用您的帳號。",
                )
            else:
                # 帳號被停用
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您的帳戶已被停用，無法登入系統。如有疑問請聯絡管理者。",
                )

        # 5. 生成登入回應
        response = await AuthService.generate_login_response(
            db, user, ip_address, user_agent
        )

        # 記錄登入成功審計
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
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Google 登入失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google 登入失敗: {str(e)}",
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
    # 檢查電子郵件是否已存在
    existing_user = await AuthService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="該電子郵件已被註冊"
        )

    # 檢查使用者名稱是否已存在
    existing_username = await AuthService.get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="該使用者名稱已被使用"
        )

    # 建立新使用者
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


@router.post(
    "/refresh", response_model=TokenResponse, summary="刷新令牌"
)  # 回應模型改為 TokenResponse
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest,  # 接收 RefreshTokenRequest
    db: AsyncSession = Depends(get_async_db),
):
    """
    刷新存取令牌
    - **refresh_token**: 刷新令牌
    """
    # 驗證刷新令牌
    user = await AuthService.verify_refresh_token(db, refresh_request.refresh_token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效或過期的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 取得客戶端資訊
    ip_address, user_agent = get_client_info(request)

    # 撤銷舊會話 (基於刷新令牌)
    # 這裡需要找到舊會話的 jti 來撤銷，或者直接在 verify_refresh_token 中處理
    # 為了簡化，假設 verify_refresh_token 已經處理了舊會話的有效性檢查
    # 並且我們將生成一個全新的會話

    # 生成新的登入回應 (包含新的 access_token 和 refresh_token)
    return await AuthService.generate_login_response(db, user, ip_address, user_agent)


@router.post("/logout", summary="使用者登出")
async def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """使用者登出 - 撤銷當前會話"""
    # 開發模式下允許無 token 登出
    if settings.AUTH_DISABLED:
        logger.info("[AUTH] 開發模式 - 登出請求（無需驗證）")
        return {"message": "登出成功（開發模式）"}

    # 檢查是否有提供認證資訊
    if not credentials or not credentials.credentials:
        # 沒有 token 也視為成功登出（可能是 token 已過期）
        logger.info("[AUTH] 登出請求（無 token）")
        return {"message": "登出成功"}

    token = credentials.credentials
    payload = AuthService.verify_token(token)

    if not payload:
        # token 無效也視為成功登出
        logger.info("[AUTH] 登出請求（token 無效或已過期）")
        return {"message": "登出成功"}

    jti = payload.get("jti")
    user_id = payload.get("sub")
    email = payload.get("email")
    ip_address, user_agent = get_client_info(request)

    if jti:
        await AuthService.revoke_session(db, jti)

    # 記錄登出審計
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


def is_internal_ip(ip_address: Optional[str]) -> bool:
    """
    檢測是否為內網 IP
    內網 IP 範圍：
    - 10.x.x.x (Class A private)
    - 172.16-31.x.x (Class B private)
    - 192.168.x.x (Class C private)
    - localhost (127.0.0.1)
    """
    if not ip_address:
        return False

    import re as regex_module

    internal_patterns = [
        r"^10\.",  # 10.0.0.0 - 10.255.255.255
        r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",  # 172.16.0.0 - 172.31.255.255
        r"^192\.168\.",  # 192.168.0.0 - 192.168.255.255
        r"^127\.",  # localhost
    ]

    return any(regex_module.match(pattern, ip_address) for pattern in internal_patterns)


def get_superuser_mock() -> User:
    """返回模擬的超級管理員使用者"""
    dev_permissions = [
        "documents:read",
        "documents:create",
        "documents:edit",
        "documents:delete",
        "projects:read",
        "projects:create",
        "projects:edit",
        "projects:delete",
        "agencies:read",
        "agencies:create",
        "agencies:edit",
        "agencies:delete",
        "vendors:read",
        "vendors:create",
        "vendors:edit",
        "vendors:delete",
        "calendar:read",
        "calendar:edit",
        "reports:view",
        "reports:export",
        "system_docs:read",
        "system_docs:create",
        "system_docs:edit",
        "system_docs:delete",
        "admin:users",
        "admin:settings",
        "admin:site_management",
        "admin:database",
    ]

    return User(
        id=1,
        email="superuser@dev.example",  # 使用有效的 email 格式
        username="superuser",
        full_name="(Internal) SuperUser",
        is_active=True,
        is_admin=True,
        is_superuser=True,
        permissions=json.dumps(dev_permissions),
        role="superuser",
        auth_provider="internal",  # 現在 AuthProvider 已支援 'internal'
        login_count=0,
        email_verified=True,
        created_at=datetime.utcnow(),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    取得當前認證使用者 - 依賴注入函數

    權限控制說明：
    - 使用 settings.AUTH_DISABLED 環境變數控制開發模式
    - 生產環境必須設為 False
    - 開發模式下會返回模擬的超級管理員
    """
    # 使用環境變數控制開發模式（從 config.py 讀取）
    if settings.AUTH_DISABLED:
        logger.warning("[AUTH] 開發模式 - 認證已停用，回傳模擬管理員使用者")
        # 在開發模式下，直接回傳一個模擬使用者，避免資料庫依賴
        dev_permissions = [
            "documents:read",
            "documents:create",
            "documents:edit",
            "documents:delete",
            "projects:read",
            "projects:create",
            "projects:edit",
            "projects:delete",
            "agencies:read",
            "agencies:create",
            "agencies:edit",
            "agencies:delete",
            "vendors:read",
            "vendors:create",
            "vendors:edit",
            "vendors:delete",
            "calendar:read",
            "calendar:edit",
            "reports:view",
            "reports:export",
            "system_docs:read",
            "system_docs:create",
            "system_docs:edit",
            "system_docs:delete",
            "admin:users",
            "admin:settings",
            "admin:site_management",
        ]

        return User(
            id=1,
            email="dev@example.com",
            username="dev-admin",
            full_name="開發者管理員",
            is_active=True,
            is_admin=True,
            is_superuser=True,
            permissions=json.dumps(dev_permissions),
            role="superuser",
            auth_provider="email",
            login_count=0,
            email_verified=True,
            created_at=datetime.utcnow(),
        )

    # 認證已啟用，執行正常的認證流程
    try:
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

        return user
    except Exception as e:
        print(f"ERROR in get_current_user: {e}")
        raise


@router.post("/me", response_model=UserProfile, summary="取得當前使用者資訊")
async def get_current_user_info(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得當前登入使用者的詳細資訊 (POST-only 安全模式)

    內網 IP 無需認證即可獲得超級管理員身份
    """
    # 取得客戶端 IP
    ip_address = request.client.host if request.client else None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()

    # 檢查是否為內網 IP 或開發模式
    # 🔧 修復：在 localhost 開發時，不使用超級用戶模擬，使用實際認證
    is_development_localhost = (
        ip_address in ["127.0.0.1", "localhost"] and settings.DEVELOPMENT_MODE
    )

    if settings.AUTH_DISABLED and not is_development_localhost:
        logger.info(
            f"[AUTH] Internal/Dev access - IP: {ip_address}, AUTH_DISABLED: {settings.AUTH_DISABLED}"
        )
        return UserProfile.model_validate(get_superuser_mock())

    # 🎯 確保 CORS 設定正確 - 對於開發模式，移除超級用戶檢查，直接使用正常認證流程

    # 正常認證流程 (包括 localhost 開發模式)

    # 正常認證流程
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


@router.post("/profile/update", response_model=UserProfile, summary="更新個人資料")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    更新當前使用者的個人資料

    - **username**: 使用者名稱（可選）
    - **full_name**: 完整姓名（可選）
    """
    logger.info(f"[AUTH] 更新個人資料: user_id={current_user.id}")

    try:
        # 從資料庫重新取得使用者（確保是可更新的實體）
        stmt = select(User).where(User.id == current_user.id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="使用者不存在"
            )

        # 檢查使用者名稱是否已被其他人使用
        if profile_data.username and profile_data.username != user.username:
            existing_user = await AuthService.get_user_by_username(db, profile_data.username)
            if existing_user and existing_user.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="該使用者名稱已被使用"
                )
            user.username = profile_data.username

        # 更新姓名
        if profile_data.full_name is not None:
            user.full_name = profile_data.full_name

        await db.commit()
        await db.refresh(user)

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
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    修改當前使用者的密碼

    - **current_password**: 目前密碼
    - **new_password**: 新密碼（至少 6 個字元）

    注意：僅適用於 email 認證方式的使用者，Google OAuth 使用者無法修改密碼
    """
    logger.info(f"[AUTH] 修改密碼請求: user_id={current_user.id}")

    # 檢查認證方式
    if current_user.auth_provider == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google 帳號使用者無法修改密碼，請透過 Google 管理您的密碼"
        )

    try:
        # 從資料庫重新取得使用者
        stmt = select(User).where(User.id == current_user.id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="使用者不存在"
            )

        # 驗證目前密碼
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

        # 更新密碼
        user.password_hash = AuthService.get_password_hash(password_data.new_password)
        await db.commit()

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

