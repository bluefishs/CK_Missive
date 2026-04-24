"""
使用者認證相關的 Pydantic 模型
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict # 新增 ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class AuthProvider(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    LINE = "line"
    INTERNAL = "internal"  # 內網免認證模式

class UserRole(str, Enum):
    UNVERIFIED = "unverified"
    USER = "user"
    STAFF = "staff"  # 承辦同仁
    ADMIN = "admin"
    SUPERUSER = "superuser"

# === 請求模型 ===

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., description="Google OAuth ID Token")
    
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)

class ProfileUpdate(BaseModel):
    """更新個人資料請求"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    department: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)

class PasswordReset(BaseModel):
    """密碼重設請求"""
    email: EmailStr = Field(..., description="註冊的電子郵件")

class PasswordResetConfirm(BaseModel):
    """密碼重設確認"""
    token: str = Field(..., description="重設 token")
    new_password: str = Field(..., min_length=12, max_length=100, description="新密碼")

class RefreshTokenRequest(BaseModel): # 新增 RefreshTokenRequest
    refresh_token: str = Field(..., description="刷新令牌")

# === 回應模型 ===

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    auth_provider: AuthProvider = AuthProvider.EMAIL
    avatar_url: Optional[str] = None
    role: UserRole = UserRole.USER

class UserResponse(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    login_count: int = 0
    email_verified: bool = False
    role: Optional[str] = None  # 覆寫為字串，支援中文角色名稱如 '專案PM'
    department: Optional[str] = None
    position: Optional[str] = None
    # 多 provider 追蹤 (管理員用)
    line_user_id: Optional[str] = None
    line_display_name: Optional[str] = None
    google_id: Optional[str] = None
    auth_providers: List[str] = []

    # ADR-0025 Identity Unification：以 full_name 為群組聚合 canonical + aliases
    canonical_user_id: Optional[int] = None
    alias_count: int = 0                 # 本 user 名下的 alias 數（canonical 視角）
    alias_emails: List[str] = []         # alias 們的 email 列表
    merged_auth_providers: List[str] = []  # canonical + aliases 的 providers 聯集

    model_config = ConfigDict(from_attributes=True) # 使用 model_config

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """覆寫 model_validate 以自動計算 auth_providers。

        v5.8.0：若 ORM 物件帶 `aliases` collection（canonical 角度），
        自動聚合 alias_count / alias_emails / merged_auth_providers。
        """
        instance = super().model_validate(obj, **kwargs)

        def _providers_of(u) -> List[str]:
            ps: List[str] = []
            if getattr(u, 'password_hash', None):
                ps.append('email')
            if getattr(u, 'google_id', None):
                ps.append('google')
            if getattr(u, 'line_user_id', None):
                ps.append('line')
            if getattr(u, 'auth_provider', None) == 'internal':
                ps.append('internal')
            if not ps and getattr(u, 'auth_provider', None):
                ps.append(str(u.auth_provider))
            return ps

        # 本身 providers
        providers = _providers_of(obj)
        instance.auth_providers = providers

        # 聚合 alias 資訊（若 ORM 有 eager-load aliases relationship）
        # 用 __dict__ 而非 getattr，避免在 async session 外觸發 lazy-load → MissingGreenlet
        aliases = (obj.__dict__.get('aliases') if hasattr(obj, '__dict__') else None) or []
        if aliases:
            merged = set(providers)
            emails = []
            for a in aliases:
                merged.update(_providers_of(a))
                if getattr(a, 'email', None):
                    emails.append(a.email)
            instance.alias_count = len(aliases)
            instance.alias_emails = emails
            instance.merged_auth_providers = sorted(merged)
        else:
            instance.merged_auth_providers = providers

        return instance

class UserProfile(UserResponse):
    permissions: Optional[str] = None
    line_user_id: Optional[str] = None
    line_display_name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user_info: UserResponse
    mfa_required: bool = False
    mfa_token: Optional[str] = None

class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class GoogleUserInfo(BaseModel):
    google_id: str
    email: EmailStr
    full_name: str
    avatar_url: Optional[str] = None
    email_verified: bool = False

# === 權限相關 ===

class PermissionCheck(BaseModel):
    permission: str
    resource: Optional[str] = None

class UserPermissions(BaseModel):
    user_id: int
    permissions: List[str]
    role: UserRole

# === 會話管理 ===

class SessionInfo(BaseModel):
    id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    created_at: datetime
    last_activity: Optional[datetime] = None
    is_active: bool
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)

class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]
    total: int

class RevokeSessionRequest(BaseModel):
    session_id: int = Field(..., description="要撤銷的 Session ID")

class UserSessionsResponse(BaseModel):
    sessions: List[SessionInfo]
    current_session_id: int

# === 管理員功能 ===

class UserUpdate(BaseModel):
    """管理員更新使用者資訊 schema。

    v5.8.0 修復：補齊 department / position 等前端既有欄位，
    避免「There was an error parsing the body」400。
    """
    model_config = ConfigDict(extra='ignore')  # 忽略未知欄位而非拒絕

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    role: Optional[UserRole] = None
    permissions: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int

class UserSearchParams(BaseModel):
    q: Optional[str] = None
    role: Optional[UserRole] = None
    auth_provider: Optional[AuthProvider] = None
    is_active: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    # ADR-0025 Identity Unification：承辦同仁下拉等場景開此旗標過濾 canonical
    canonical_only: bool = Field(
        default=False,
        description="只回 canonical user（canonical_user_id IS NULL）；承辦同仁下拉用",
    )

# === 登入歷史 ===

class LoginHistoryItem(BaseModel):
    """登入歷史項目"""
    id: int
    event_type: str = Field(..., description="事件類型 (LOGIN_SUCCESS, LOGIN_FAILED, LOGIN_BLOCKED, LOGOUT, TOKEN_REFRESH)")
    auth_provider: Optional[str] = Field(None, description="登入方式 (email, google, line, internal)")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    created_at: datetime
    details: Optional[dict] = None

class LoginHistoryResponse(BaseModel):
    """登入歷史回應"""
    items: List[LoginHistoryItem]
    total: int
    page: int
    page_size: int


class AdminLoginHistoryItem(LoginHistoryItem):
    """管理員登入歷史項目 — 包含使用者資訊"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None


class AdminLoginHistoryResponse(BaseModel):
    """管理員登入歷史回應"""
    items: List[AdminLoginHistoryItem]
    total: int
    page: int
    page_size: int


# === MFA 雙因素認證 ===

class MFASetupResponse(BaseModel):
    """MFA 設定回應 - 包含 secret、QR code 和備用碼"""
    secret: str = Field(..., description="TOTP secret (base32)")
    qr_uri: str = Field(..., description="otpauth:// URI")
    qr_code_base64: str = Field(..., description="QR code PNG 圖片 (base64)")
    backup_codes: List[str] = Field(..., description="備用碼列表 (僅顯示一次)")

class MFAVerifyRequest(BaseModel):
    """MFA 驗證請求 - 確認 TOTP 並啟用 MFA"""
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", description="6 位數 TOTP 驗證碼")

class MFADisableRequest(BaseModel):
    """MFA 停用請求 - 需要密碼驗證"""
    password: str = Field(..., description="使用者密碼")

class MFAValidateRequest(BaseModel):
    """MFA 登入驗證請求"""
    mfa_token: str = Field(..., description="MFA 臨時 token")
    code: str = Field(..., min_length=1, max_length=20, description="6 位數 TOTP 驗證碼或備用碼")

class MFAStatusResponse(BaseModel):
    """MFA 狀態回應"""
    mfa_enabled: bool = Field(..., description="MFA 是否已啟用")
    backup_codes_remaining: int = Field(0, description="剩餘備用碼數量")


class VerifyEmailRequest(BaseModel):
    """驗證 Email 請求"""
    token: str = Field(..., description="Email 驗證 token")


# === LINE Login ===

class LineAuthRequest(BaseModel):
    """LINE Login OAuth callback 請求"""
    code: str = Field(..., description="LINE OAuth authorization code")
    state: Optional[str] = Field(None, description="CSRF state token")
    redirect_uri: Optional[str] = Field(None, description="前端 redirect URI (LIFF 或 Web)")

class LineBindRequest(BaseModel):
    """已登入帳號綁定 LINE"""
    code: str = Field(..., description="LINE OAuth authorization code")
    redirect_uri: Optional[str] = Field(None, description="前端 redirect URI")

class LineUserInfo(BaseModel):
    """LINE 使用者資訊 (從 ID Token 或 Profile API 取得)"""
    line_user_id: str = Field(..., description="LINE User ID (U 開頭)")
    display_name: str = Field(..., description="LINE 顯示名稱")
    picture_url: Optional[str] = Field(None, description="LINE 大頭照 URL")
    email: Optional[EmailStr] = Field(None, description="LINE 帳號 Email (需 openid email scope)")