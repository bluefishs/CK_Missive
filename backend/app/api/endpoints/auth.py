"""
認證相關API端點

v2.0 - 2026-01-09
- 主要認證方式: Google OAuth
- 傳統帳密登入: 已棄用 (保留但標記 deprecated)
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
    UserRegister, GoogleAuthRequest, TokenResponse,
    UserResponse, UserProfile, RefreshTokenRequest
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

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="傳統帳密登入 (已棄用)",
    deprecated=True,
    tags=["deprecated"]
)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    """
    ⚠️ **已棄用** - 請使用 Google OAuth 登入 (/auth/google)

    使用者傳統帳密登入
    - **username**: 使用者名稱或信箱
    - **password**: 密碼

    注意: 此端點將在未來版本移除，請改用 Google OAuth 登入。
    """
    logger.warning(f"[AUTH] 使用已棄用的帳密登入: {form_data.username}")
    try:
        # 驗證使用者
        user = await AuthService.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳號或密碼錯誤",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 取得客戶端資訊
        ip_address, user_agent = get_client_info(request)
        
        # 生成登入回應
        return await AuthService.generate_login_response(db, user, ip_address, user_agent)
        
    except HTTPException as http_exc:
        # 如果是已知的 HTTP 錯誤 (例如 401)，直接重新拋出
        raise http_exc
    except Exception as e:
        # 捕捉所有其他未預期的錯誤 (例如資料庫連線失敗)
        # logger.error(f"登入時發生未預期錯誤: {e}", exc_info=True) # 建議加入日誌記錄
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入服務內部錯誤，請稍後再試或聯繫管理員。錯誤詳情: {str(e)}"
        )

@router.post("/google", response_model=TokenResponse, summary="Google OAuth 登入")
async def google_oauth_login(
    request: Request,
    google_request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_async_db)
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
                success=False
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您的 Google 帳號網域不在允許清單內，無法登入系統。請聯絡管理者。"
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
                        "default_role": user.role
                    },
                    success=True
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
                    "reason": "pending_approval" if is_new_user else "account_deactivated"
                },
                success=False
            )

            if is_new_user:
                # 新帳號等待審核
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您的帳號已建立，但需要管理員審核後才能使用。請聯絡管理者啟用您的帳號。"
                )
            else:
                # 帳號被停用
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您的帳戶已被停用，無法登入系統。如有疑問請聯絡管理者。"
                )

        # 5. 生成登入回應
        response = await AuthService.generate_login_response(db, user, ip_address, user_agent)

        # 記錄登入成功審計
        await AuditService.log_auth_event(
            event_type="LOGIN_SUCCESS",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"auth_provider": "google"},
            success=True
        )

        logger.info(f"[AUTH] 登入成功: {user.email}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Google 登入失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google 登入失敗: {str(e)}"
        )

@router.post(
    "/register",
    response_model=UserResponse,
    summary="使用者註冊 (已棄用)",
    deprecated=True,
    tags=["deprecated"]
)
async def register_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_async_db)
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該電子郵件已被註冊"
        )
    
    # 檢查使用者名稱是否已存在
    existing_username = await AuthService.get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="該使用者名稱已被使用"
        )
    
    # 建立新使用者
    password_hash = AuthService.get_password_hash(user_data.password)
    
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        password_hash=password_hash,
        auth_provider="email",
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)

@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌") # 回應模型改為 TokenResponse
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest, # 接收 RefreshTokenRequest
    db: AsyncSession = Depends(get_async_db)
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
    db: AsyncSession = Depends(get_async_db)
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
        success=True
    )

    logger.info(f"[AUTH] 使用者登出: {email}")
    return {"message": "登出成功"}

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db)
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
            "documents:read", "documents:create", "documents:edit", "documents:delete",
            "projects:read", "projects:create", "projects:edit", "projects:delete",
            "agencies:read", "agencies:create", "agencies:edit", "agencies:delete",
            "vendors:read", "vendors:create", "vendors:edit", "vendors:delete",
            "calendar:read", "calendar:edit",
            "reports:view", "reports:export",
            "system_docs:read", "system_docs:create", "system_docs:edit", "system_docs:delete",
            "admin:users", "admin:settings", "admin:site_management"
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
            created_at=datetime.utcnow()
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

@router.get("/me", response_model=UserProfile, summary="取得當前使用者資訊")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """取得當前登入使用者的詳細資訊"""
    return UserProfile.model_validate(current_user)

@router.get("/check", summary="檢查認證狀態")
async def check_auth_status(
    current_user: User = Depends(get_current_user)
):
    """檢查當前認證狀態"""
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "auth_provider": current_user.auth_provider,
        "is_admin": current_user.is_admin
    }