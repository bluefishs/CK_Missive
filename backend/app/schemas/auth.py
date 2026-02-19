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

    model_config = ConfigDict(from_attributes=True) # 使用 model_config

class UserProfile(UserResponse):
    permissions: Optional[str] = None

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
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    role: Optional[UserRole] = None
    permissions: Optional[str] = None

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

# === 登入歷史 ===

class LoginHistoryItem(BaseModel):
    """登入歷史項目"""
    id: int
    event_type: str = Field(..., description="事件類型 (LOGIN_SUCCESS, LOGIN_FAILED, LOGIN_BLOCKED, LOGOUT, TOKEN_REFRESH)")
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