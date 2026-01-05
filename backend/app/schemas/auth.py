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

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=100)

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
    
    model_config = ConfigDict(from_attributes=True) # 使用 model_config

class UserProfile(UserResponse):
    permissions: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user_info: UserResponse

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
    last_activity: datetime
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True) # 使用 model_config

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