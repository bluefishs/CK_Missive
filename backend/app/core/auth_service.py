"""
認證服務 - JWT 令牌管理、Google OAuth 驗證與權限檢查

v2.1 - 2026-02-07
- 新增 httpOnly cookie 認證支援
- 新增 set_auth_cookies / clear_auth_cookies 方法
- 保留 Authorization header 向後相容（過渡期）

v2.0 - 2026-01-09
- 簡化為僅 Google OAuth 認證
- 新增網域白名單檢查
- 新增新帳號審核機制
"""
import json
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from google.oauth2 import id_token
from google.auth.transport import requests
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from starlette.responses import Response

from app.core.config import settings
from app.core.csrf import generate_csrf_token, set_csrf_cookie
from app.extended.models import User, UserSession
from app.schemas.auth import UserResponse, GoogleUserInfo, TokenResponse

logger = logging.getLogger(__name__)

# 密碼加密設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 設定
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# HTTP Bearer 認證
security = HTTPBearer(auto_error=False)  # 不自動拋出錯誤，讓 get_current_user 處理

class AuthService:
    """
    認證服務類別

    v2.0 - 僅支援 Google OAuth 認證
    """

    # ============ 網域白名單檢查 ============

    @staticmethod
    def get_allowed_domains() -> List[str]:
        """取得允許的 Google 網域清單"""
        domains_str = settings.GOOGLE_ALLOWED_DOMAINS or ""
        if not domains_str.strip():
            return []  # 空白表示允許所有
        return [d.strip().lower() for d in domains_str.split(",") if d.strip()]

    @staticmethod
    def check_email_domain(email: str) -> bool:
        """
        檢查 email 是否在允許的網域內

        Args:
            email: 使用者 email

        Returns:
            True 表示允許，False 表示拒絕
        """
        allowed_domains = AuthService.get_allowed_domains()
        if not allowed_domains:
            return True  # 未設定白名單，允許所有

        email_domain = email.split("@")[-1].lower()
        is_allowed = email_domain in allowed_domains

        if not is_allowed:
            logger.warning(f"[AUTH] 網域被拒: {email_domain} 不在允許清單 {allowed_domains}")

        return is_allowed

    @staticmethod
    def should_auto_activate() -> bool:
        """檢查新帳號是否應自動啟用"""
        return settings.AUTO_ACTIVATE_NEW_USER

    @staticmethod
    def get_default_user_role() -> str:
        """取得新帳號預設角色"""
        return settings.DEFAULT_USER_ROLE or "user"

    @staticmethod
    def get_default_permissions() -> str:
        """取得新帳號預設權限"""
        default_permissions = [
            "documents:read",
            "projects:read",
            "agencies:read",
            "vendors:read",
            "calendar:read",
            "reports:view"
        ]
        return json.dumps(default_permissions)

    # ============ 密碼相關 (保留但標記棄用) ============

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """驗證密碼 - 僅支援 bcrypt 雜湊比較"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"bcrypt 驗證異常（可能是非法 hash 格式）: {type(e).__name__}")
            return False
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密碼雜湊"""
        return pwd_context.hash(password)

    @staticmethod
    def validate_password_strength(
        password: str,
        username: str = None,
        raise_on_invalid: bool = False
    ) -> tuple:
        """
        驗證密碼強度

        Args:
            password: 要驗證的密碼
            username: 可選的用戶名，用於檢查相似度
            raise_on_invalid: 如果為 True，驗證失敗時拋出異常

        Returns:
            tuple: (是否有效, 訊息)

        Raises:
            ValueError: 當 raise_on_invalid=True 且密碼不符合要求時
        """
        from app.core.password_policy import validate_password
        is_valid, message = validate_password(password, username)
        if not is_valid and raise_on_invalid:
            raise ValueError(message)
        return is_valid, message
    
    @staticmethod
    def generate_token_jti() -> str:
        """生成唯一的 JWT ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None,
        jti: Optional[str] = None
    ) -> str:
        """建立存取令牌"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti or AuthService.generate_token_jti()
        })
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token() -> str:
        """建立刷新令牌"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """驗證令牌並回傳載荷"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    async def verify_google_token(credential: str) -> GoogleUserInfo:
        """驗證 Google OAuth ID Token"""
        try:
            # 驗證 Google ID Token
            idinfo = id_token.verify_oauth2_token(
                credential, 
                requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            # 檢查 token 發行者
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            # 提取使用者資訊
            return GoogleUserInfo(
                google_id=idinfo['sub'],
                email=idinfo['email'],
                full_name=idinfo.get('name', ''),
                avatar_url=idinfo.get('picture'),
                email_verified=idinfo.get('email_verified', False)
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Google token: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google authentication error: {str(e)}"
            )
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, username_or_email: str, password: str) -> Optional[User]:
        """驗證使用者帳密 - 支持email或username登入"""
        # 嘗試通過email查找用戶
        result = await db.execute(
            select(User).where(
                User.email == username_or_email,
                User.is_active == True
            )
        )
        user = result.scalar_one_or_none()
        
        # 如果email找不到，嘗試通過username查找
        if not user:
            result = await db.execute(
                select(User).where(
                    User.username == username_or_email,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()
        
        if not user or not user.password_hash:
            return None
        
        if not AuthService.verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    async def get_user_by_google_id(db: AsyncSession, google_id: str) -> Optional[User]:
        """透過 Google ID 取得使用者"""
        result = await db.execute(
            select(User).where(
                User.google_id == google_id,
                User.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """透過電子郵件取得使用者"""
        result = await db.execute(
            select(User).where(
                User.email == email,
                User.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user_session(
        db: AsyncSession,
        user: User,
        token_jti: str,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """建立使用者會話"""
        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        session = UserSession(
            user_id=user.id,
            token_jti=token_jti,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        return session
    
    @staticmethod
    async def revoke_session(db: AsyncSession, token_jti: str) -> bool:
        """撤銷會話"""
        result = await db.execute(
            update(UserSession)
            .where(UserSession.token_jti == token_jti)
            .values(
                is_active=False,
                revoked_at=datetime.utcnow()
            )
        )
        await db.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def update_user_login_info(db: AsyncSession, user: User):
        """更新使用者登入資訊"""
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                last_login=datetime.utcnow(),
                login_count=User.login_count + 1
            )
        )
        await db.commit()
    
    @staticmethod
    async def verify_refresh_token(db: AsyncSession, refresh_token: str) -> Optional[User]:
        """
        驗證刷新令牌並返回相關聯的使用者。

        安全機制 (Refresh Token Rotation):
        - 使用 SELECT FOR UPDATE 防止並發競態
        - 驗證成功後，舊的 session 會被撤銷
        - 偵測已撤銷 token 重複使用（token replay attack），自動撤銷該用戶所有 session
        """
        # 使用 FOR UPDATE 鎖定行，防止並發 refresh 競態
        session_result = await db.execute(
            select(UserSession).where(
                UserSession.refresh_token == refresh_token,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ).with_for_update()
        )
        session = session_result.scalar_one_or_none()

        if not session:
            # Token Replay 偵測：檢查此 token 是否已被撤銷過
            replay_result = await db.execute(
                select(UserSession).where(
                    UserSession.refresh_token == refresh_token,
                    UserSession.is_active == False
                )
            )
            replay_session = replay_result.scalar_one_or_none()
            if replay_session:
                # 已撤銷的 token 被重複使用 → 可能被竊取
                logger.critical(
                    f"[AUTH] Refresh token replay detected! "
                    f"user_id={replay_session.user_id}, jti={replay_session.token_jti}"
                )
                # 撤銷該用戶的所有 session
                await db.execute(
                    update(UserSession)
                    .where(
                        UserSession.user_id == replay_session.user_id,
                        UserSession.is_active == True
                    )
                    .values(is_active=False, revoked_at=datetime.utcnow())
                )
                await db.commit()
            return None

        # 獲取相關聯的使用者
        user_result = await db.execute(
            select(User).where(
                User.id == session.user_id,
                User.is_active == True
            )
        )
        user = user_result.scalar_one_or_none()

        if not user:
            await AuthService.revoke_session(db, session.token_jti)
            return None

        # Refresh Token Rotation: 撤銷舊 session，確認撤銷成功
        revoked = await AuthService.revoke_session(db, session.token_jti)
        if not revoked:
            logger.error(f"[AUTH] Failed to revoke session during rotation: jti={session.token_jti}")
            return None

        logger.info(f"[AUTH] Refresh token rotated: user_id={user.id}, old_jti={session.token_jti}")
        return user

    @staticmethod
    async def create_oauth_user(
        db: AsyncSession, 
        google_info: GoogleUserInfo,
        username: Optional[str] = None
    ) -> User:
        """建立 OAuth 使用者"""
        # 如果沒有提供 username，使用 email 的本地部分
        if not username:
            username = google_info.email.split('@')[0]
        
        # 確保 username 唯一
        counter = 1
        original_username = username
        while await AuthService.get_user_by_username(db, username):
            username = f"{original_username}{counter}"
            counter += 1
        
        user = User(
            email=google_info.email,
            username=username,
            full_name=google_info.full_name,
            google_id=google_info.google_id,
            avatar_url=google_info.avatar_url,
            auth_provider="google",
            email_verified=google_info.email_verified,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """透過使用者名稱取得使用者"""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_current_user_from_token(db: AsyncSession, token: str) -> Optional[User]:
        """從令牌取得當前使用者"""
        payload = AuthService.verify_token(token)
        if not payload:
            return None
        
        user_id_str = payload.get("sub")
        jti = payload.get("jti")
        
        if not user_id_str or not jti:
            return None
        
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            return None
        
        # 檢查會話是否有效 - 使用 raw SQL 避免類型轉換問題
        from sqlalchemy import text
        session_result = await db.execute(
            text("""
                SELECT * FROM user_sessions 
                WHERE token_jti = :token_jti 
                AND is_active = true 
                AND expires_at > :current_time
            """),
            {"token_jti": jti, "current_time": datetime.utcnow()}
        )
        session_row = session_result.fetchone()
        
        if not session_row:
            return None
        
        # 使用 text() 直接查詢避免類型轉換問題
        result = await db.execute(
            text("SELECT * FROM users WHERE id = :user_id AND is_active = true"),
            {"user_id": user_id}
        )
        user_row = result.fetchone()
        
        if not user_row:
            return None
        
        # 手動創建 User 對象
        user = User(
            id=user_row.id,
            email=user_row.email,
            username=user_row.username,
            full_name=user_row.full_name,
            password_hash=user_row.password_hash,
            is_active=user_row.is_active,
            is_admin=user_row.is_admin,
            is_superuser=user_row.is_superuser,
            google_id=user_row.google_id,
            avatar_url=user_row.avatar_url,
            auth_provider=user_row.auth_provider,
            last_login=user_row.last_login,
            login_count=user_row.login_count,
            permissions=user_row.permissions,
            role=user_row.role,
            created_at=user_row.created_at,
            updated_at=user_row.updated_at,
            email_verified=user_row.email_verified
        )
        
        # 更新最後活動時間 - 使用 raw SQL
        await db.execute(
            text("UPDATE user_sessions SET last_activity = :current_time WHERE token_jti = :token_jti"),
            {"current_time": datetime.utcnow(), "token_jti": jti}
        )
        await db.commit()
        
        return user
    
    @staticmethod
    def check_permission(user: User, required_permission: str) -> bool:
        """檢查使用者權限"""
        if user.is_superuser:
            return True
        
        if not user.permissions:
            return False
        
        try:
            permissions = json.loads(user.permissions)
            return required_permission in permissions
        except (json.JSONDecodeError, TypeError):
            return False
    
    @staticmethod
    def check_admin_permission(user: User) -> bool:
        """檢查管理員權限"""
        return user.is_admin or user.is_superuser
    
    # ============ httpOnly Cookie 認證 (v2.1) ============

    @staticmethod
    def set_auth_cookies(response: Response, token_data: TokenResponse) -> None:
        """
        設定認證相關的 httpOnly cookies

        設定項目:
        - access_token: HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=3600
        - refresh_token: HttpOnly; Secure; SameSite=Strict; Path=/api/auth/refresh; Max-Age=604800
        - csrf_token: non-HttpOnly (由 csrf 模組處理)

        Args:
            response: FastAPI/Starlette Response 物件
            token_data: 包含 access_token 和 refresh_token 的 TokenResponse
        """
        is_dev = settings.DEVELOPMENT_MODE

        # 設定 access_token cookie
        response.set_cookie(
            key="access_token",
            value=token_data.access_token,
            httponly=True,
            secure=not is_dev,  # 開發環境允許 HTTP
            samesite="lax",
            path="/",
            max_age=token_data.expires_in,  # 使用 token 本身的過期時間
        )

        # 設定 refresh_token cookie
        if token_data.refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=token_data.refresh_token,
                httponly=True,
                secure=not is_dev,
                samesite="strict",  # refresh token 使用更嚴格的 SameSite
                path="/api/auth/refresh",  # 限制只在 refresh 端點發送
                max_age=604800,  # 7 天
            )

        # 設定 CSRF token（non-httpOnly，前端 JS 需要讀取）
        csrf_token = generate_csrf_token()
        set_csrf_cookie(response, csrf_token, is_development=is_dev)

        logger.info("[AUTH] 已設定認證 cookies (access_token, refresh_token, csrf_token)")

    @staticmethod
    def clear_auth_cookies(response: Response) -> None:
        """
        清除所有認證相關的 cookies

        Args:
            response: FastAPI/Starlette Response 物件
        """
        from app.core.csrf import clear_csrf_cookie

        response.delete_cookie(key="access_token", path="/")
        response.delete_cookie(key="refresh_token", path="/api/auth/refresh")
        clear_csrf_cookie(response)

        logger.info("[AUTH] 已清除認證 cookies")

    @staticmethod
    async def generate_login_response(
        db: AsyncSession,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        is_refresh: bool = False
    ) -> TokenResponse:
        """
        生成登入回應包含令牌和使用者資訊

        Args:
            is_refresh: True 表示由 refresh token 觸發，不更新 login_count
        """
        # 生成令牌
        jti = AuthService.generate_token_jti()
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        access_token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires,
            jti=jti
        )

        refresh_token = AuthService.create_refresh_token()

        # 建立會話
        await AuthService.create_user_session(
            db, user, jti, refresh_token, ip_address, user_agent
        )

        # 僅在正式登入時更新登入次數（refresh 不算新登入）
        if not is_refresh:
            await AuthService.update_user_login_info(db, user)

        # 重新取得使用者資料 (包含更新後的登入資訊)
        await db.refresh(user)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            user_info=UserResponse.model_validate(user)
        )