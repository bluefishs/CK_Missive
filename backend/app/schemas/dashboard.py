"""
儀表板 API Schema 定義

提供儀表板相關端點的統一回應格式。

@version 1.0.0
@date 2026-01-20
"""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ============================================================================
# 基礎統計 Schema
# ============================================================================

class DashboardStats(BaseModel):
    """儀表板基本統計"""
    total: int = Field(..., description="總數")
    approved: int = Field(0, description="已核准數")
    pending: int = Field(0, description="待處理數")
    rejected: int = Field(0, description="已拒絕數")


class DocumentTypeCount(BaseModel):
    """公文類型統計"""
    type: str = Field(..., description="類型名稱")
    count: int = Field(..., description="數量")


# ============================================================================
# 儀表板主要 Response Schema
# ============================================================================

class DashboardStatsResponse(BaseModel):
    """儀表板統計回應 - /dashboard/stats"""
    stats: DashboardStats
    recent_documents: List[Any] = Field(default_factory=list, description="最近公文列表")

    model_config = {"from_attributes": True}


class StatisticsOverviewResponse(BaseModel):
    """統計概覽回應 - /dashboard/statistics/overview"""
    total_documents: int = Field(0, description="公文總數")
    document_types: List[DocumentTypeCount] = Field(default_factory=list, description="按類型統計")
    total_users: int = Field(0, description="使用者總數")
    active_users: int = Field(0, description="活躍使用者數")

    model_config = {"from_attributes": True}


# ============================================================================
# 行事曆統計 Response Schema
# ============================================================================

class CalendarStatsItem(BaseModel):
    """行事曆統計項目"""
    event_type: str = Field(..., description="事件類型")
    count: int = Field(..., description="數量")
    color: Optional[str] = Field(None, description="顯示顏色")


class CalendarStatsResponse(BaseModel):
    """行事曆統計回應 - /dashboard/pure-calendar-stats"""
    total_events: int = Field(0, description="事件總數")
    by_type: List[CalendarStatsItem] = Field(default_factory=list, description="按類型統計")
    upcoming_count: int = Field(0, description="即將到來的事件數")

    model_config = {"from_attributes": True}


class CalendarCategoryItem(BaseModel):
    """行事曆分類項目"""
    value: str = Field(..., description="分類值")
    label: str = Field(..., description="顯示標籤")
    color: str = Field(..., description="顯示顏色")


class CalendarCategoriesResponse(BaseModel):
    """行事曆分類回應 - /dashboard/pure-calendar-categories"""
    categories: List[CalendarCategoryItem] = Field(default_factory=list, description="分類列表")

    model_config = {"from_attributes": True}


# ============================================================================
# 使用者管理 Response Schema
# ============================================================================

class UserManagementUserItem(BaseModel):
    """使用者管理項目"""
    id: int
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool = True
    role: Optional[str] = None


class UserManagementUsersResponse(BaseModel):
    """使用者列表回應 - /dashboard/user-management-users"""
    users: List[UserManagementUserItem] = Field(default_factory=list)
    total: int = Field(0)

    model_config = {"from_attributes": True}


class PermissionItem(BaseModel):
    """權限項目"""
    key: str
    name: str
    description: Optional[str] = None


class UserManagementPermissionsResponse(BaseModel):
    """權限列表回應 - /dashboard/user-management-permissions"""
    permissions: List[PermissionItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ============================================================================
# 開發用 Response Schema
# ============================================================================

class ApiMappingItem(BaseModel):
    """API 對應項目"""
    path: str
    methods: List[str]
    name: Optional[str] = None


class DevMappingResponse(BaseModel):
    """API 對應關係回應 - /dashboard/dev-mapping"""
    api_mappings: List[ApiMappingItem] = Field(default_factory=list)
    total_endpoints: int = Field(0)

    model_config = {"from_attributes": True}
