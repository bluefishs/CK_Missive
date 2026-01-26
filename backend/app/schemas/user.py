"""
使用者管理 Pydantic Schema

使用統一回應格式
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator

from app.schemas.common import PaginatedResponse, PaginationMeta, SortOrder

# 專案角色選項 (承辦同仁專用)
ALLOWED_PROJECT_ROLES = ['計畫主持', '計畫協同', '專案PM', '職安主管']
# 系統角色選項 (權限管理專用)
ALLOWED_SYSTEM_ROLES = ['user', 'admin', 'superuser']


class UserBase(BaseModel):
    """使用者基礎 Schema"""
    username: str = Field(..., min_length=3, max_length=50, description="帳號")
    email: EmailStr = Field(..., description="電子郵件")
    full_name: Optional[str] = Field(None, max_length=100, description="姓名")
    role: Optional[str] = Field('專案PM', max_length=50, description="專案角色")
    is_active: bool = Field(True, description="是否啟用")
    department: Optional[str] = Field(None, max_length=100, description="部門名稱")
    position: Optional[str] = Field(None, max_length=100, description="職稱")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v:
            # 允許專案角色和系統角色
            all_roles = ALLOWED_PROJECT_ROLES + ALLOWED_SYSTEM_ROLES
            if v not in all_roles:
                raise ValueError(f'角色必須是以下之一: {all_roles}')
        return v


class UserCreate(UserBase):
    """建立使用者 Schema"""
    password: str = Field(..., min_length=6, description="密碼")


class UserUpdate(BaseModel):
    """更新使用者 Schema"""
    email: Optional[EmailStr] = Field(None, description="電子郵件")
    full_name: Optional[str] = Field(None, max_length=100, description="姓名")
    role: Optional[str] = Field(None, max_length=50, description="專案角色")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    password: Optional[str] = Field(None, min_length=6, description="新密碼")
    department: Optional[str] = Field(None, max_length=100, description="部門名稱")
    position: Optional[str] = Field(None, max_length=100, description="職稱")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v:
            all_roles = ALLOWED_PROJECT_ROLES + ALLOWED_SYSTEM_ROLES
            if v not in all_roles:
                raise ValueError(f'角色必須是以下之一: {all_roles}')
        return v


class UserStatusUpdate(BaseModel):
    """更新使用者狀態 Schema"""
    is_active: bool = Field(..., description="是否啟用")


class UserResponse(BaseModel):
    """使用者回應 Schema"""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    department: Optional[str] = None
    position: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(PaginatedResponse):
    """
    使用者列表回應 Schema（統一分頁格式）

    回應格式：
    {
        "success": true,
        "items": [...],
        "pagination": { "total": 100, "page": 1, "limit": 20, ... }
    }
    """
    items: List[UserResponse] = Field(default=[], description="使用者列表")


# 保留舊版格式供向後相容（已棄用）
class UserListResponseLegacy(BaseModel):
    """使用者列表回應 Schema（舊版格式，已棄用）"""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class UserListQuery(BaseModel):
    """使用者列表查詢參數（統一格式）"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    role: Optional[str] = Field(None, description="角色篩選")
    is_active: Optional[bool] = Field(None, description="啟用狀態篩選")
    department: Optional[str] = Field(None, description="部門篩選")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.ASC, description="排序方向")
