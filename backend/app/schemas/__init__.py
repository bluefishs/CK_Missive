#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schemas 模組匯出

統一匯出所有 Pydantic Schema 定義。
v1.1.0 - 移除 wildcard import，使用具體導入
"""

# 通用 Schema
from app.schemas.common import (
    # 錯誤相關
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    # 成功回應
    SuccessResponse,
    # 分頁相關
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,
    # 排序相關
    SortOrder,
    SortParams,
    # 查詢基類
    BaseQueryParams,
    # 通用回應
    DeleteResponse,
    BatchOperationResponse,
    # 健康檢查
    HealthStatus,
    HealthCheckResponse,
    # 下拉選項
    SelectOption,
    SelectOptionInt,
    SelectOptionStr,
)

# 認證相關
from app.schemas.auth import (
    AuthProvider,
    UserRole,
    UserRegister,
    UserLogin,
    GoogleAuthRequest,
    PasswordChange,
    ProfileUpdate,
    PasswordReset,
    PasswordResetConfirm,
    RefreshTokenRequest,
    UserBase,
    UserResponse,
    UserProfile,
    TokenResponse,
    RefreshTokenResponse,
    GoogleUserInfo,
    PermissionCheck,
    UserPermissions,
    SessionInfo,
    UserSessionsResponse,
    UserUpdate,
    UserListResponse,
    UserSearchParams,
)

# 公文相關
from app.schemas.document import (
    DocumentCategory,
    DocumentStatus,
    DocumentType,
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    StaffInfo,
    DocumentResponse,
    DocumentFilter,
    DocumentListQuery,
    DocumentImportData,
    DocumentImportResult,
    DocumentListResponse,
    DocumentListResponseLegacy,
    DocumentStats,
    ExportRequest,
    DocumentCreateRequest,
    DocumentUpdateRequest,
    DocumentSearchRequest,
)

# 專案相關
from app.schemas.project import (
    ProjectBase,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectListResponseLegacy,
    ProjectOption,
    ProjectListQuery,
)

# 廠商相關
from app.schemas.vendor import (
    VendorBase,
    VendorCreate,
    VendorUpdate,
    Vendor,
    VendorListQuery,
    VendorStatisticsResponse,
)

# 機關相關
from app.schemas.agency import (
    AgencyBase,
    AgencyCreate,
    AgencyUpdate,
    Agency,
    AgencyWithStats,
    CategoryStat,
    AgencyStatistics,
    AgenciesResponse,
    AgencyListQuery,
    AgencyListResponse,
    AgencySuggestRequest,
    AgencySuggestResponse,
    AssociationSummary,
    BatchAssociateRequest,
    BatchAssociateResponse,
    FixAgenciesRequest,
    FixAgenciesResponse,
)

# 專案廠商關聯
from app.schemas.project_vendor import (
    ProjectVendorBase,
    ProjectVendorCreate,
    ProjectVendorUpdate,
    ProjectVendorResponse,
    ProjectVendorListResponse,
    VendorProjectResponse,
    VendorProjectListResponse,
    VendorAssociationListQuery,
)

# 專案人員關聯
from app.schemas.project_staff import (
    ProjectStaffBase,
    ProjectStaffCreate,
    ProjectStaffUpdate,
    ProjectStaffResponse,
    ProjectStaffListResponse,
    StaffListQuery,
)

# 行事曆相關 (calendar.py 已歸檔至 _archived，使用 document_calendar.py)
from app.schemas.document_calendar import (
    SyncStatusResponse,
    EventListRequest,
    EventDetailRequest,
    EventDeleteRequest,
    EventSyncRequest,
    BulkSyncRequest,
    UserEventsRequest,
    ReminderConfig,
    DocumentCalendarEventCreate,
    IntegratedEventCreate,
    DocumentCalendarEventUpdate,
    DocumentCalendarEventResponse,
    ConflictCheckRequest,
    SyncIntervalRequest,
)

# 網站管理
from app.schemas.site_management import (
    NavigationItemBase,
    NavigationItemCreate,
    NavigationItemUpdate,
    NavigationItemResponse,
    NavigationTreeResponse,
    NavigationItemListResponse,
    NavigationSortItem,
    NavigationSortRequest,
    SiteConfigBase,
    SiteConfigCreate,
    SiteConfigUpdate,
    SiteConfigResponse,
    SiteConfigListResponse,
    BulkOperationRequest,
    BulkOperationResponse,
    DefaultNavigationData,
)

# AI 相關
from app.schemas.ai import (
    ParsedSearchIntent,
    NaturalSearchRequest,
    AttachmentInfo,
    DocumentSearchResult,
    NaturalSearchResponse,
)

__all__ = [
    # Common
    "ErrorCode",
    "ErrorDetail",
    "ErrorResponse",
    "SuccessResponse",
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "SortOrder",
    "SortParams",
    "BaseQueryParams",
    "DeleteResponse",
    "BatchOperationResponse",
    "HealthStatus",
    "HealthCheckResponse",
    "SelectOption",
    "SelectOptionInt",
    "SelectOptionStr",
    # Auth
    "AuthProvider",
    "UserRole",
    "UserRegister",
    "UserLogin",
    "GoogleAuthRequest",
    "PasswordChange",
    "ProfileUpdate",
    "PasswordReset",
    "PasswordResetConfirm",
    "RefreshTokenRequest",
    "UserBase",
    "UserResponse",
    "UserProfile",
    "TokenResponse",
    "RefreshTokenResponse",
    "GoogleUserInfo",
    "PermissionCheck",
    "UserPermissions",
    "SessionInfo",
    "UserSessionsResponse",
    "UserUpdate",
    "UserListResponse",
    "UserSearchParams",
    # Document
    "DocumentCategory",
    "DocumentStatus",
    "DocumentType",
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "StaffInfo",
    "DocumentResponse",
    "DocumentFilter",
    "DocumentListQuery",
    "DocumentImportData",
    "DocumentImportResult",
    "DocumentListResponse",
    "DocumentListResponseLegacy",
    "DocumentStats",
    "ExportRequest",
    "DocumentCreateRequest",
    "DocumentUpdateRequest",
    "DocumentSearchRequest",
    # Project
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListResponse",
    "ProjectListResponseLegacy",
    "ProjectOption",
    "ProjectListQuery",
    # Vendor
    "VendorBase",
    "VendorCreate",
    "VendorUpdate",
    "Vendor",
    "VendorListQuery",
    "VendorStatisticsResponse",
    # Agency
    "AgencyBase",
    "AgencyCreate",
    "AgencyUpdate",
    "Agency",
    "AgencyWithStats",
    "CategoryStat",
    "AgencyStatistics",
    "AgenciesResponse",
    "AgencyListQuery",
    "AgencyListResponse",
    "AgencySuggestRequest",
    "AgencySuggestResponse",
    "AssociationSummary",
    "BatchAssociateRequest",
    "BatchAssociateResponse",
    "FixAgenciesRequest",
    "FixAgenciesResponse",
    # Project Vendor
    "ProjectVendorBase",
    "ProjectVendorCreate",
    "ProjectVendorUpdate",
    "ProjectVendorResponse",
    "ProjectVendorListResponse",
    "VendorProjectResponse",
    "VendorProjectListResponse",
    "VendorAssociationListQuery",
    # Project Staff
    "ProjectStaffBase",
    "ProjectStaffCreate",
    "ProjectStaffUpdate",
    "ProjectStaffResponse",
    "ProjectStaffListResponse",
    "StaffListQuery",
    # Calendar
    "SyncStatusResponse",
    "EventListRequest",
    "EventDetailRequest",
    "EventDeleteRequest",
    "EventSyncRequest",
    "BulkSyncRequest",
    "UserEventsRequest",
    "ReminderConfig",
    "DocumentCalendarEventCreate",
    "IntegratedEventCreate",
    "DocumentCalendarEventUpdate",
    "DocumentCalendarEventResponse",
    "ConflictCheckRequest",
    "SyncIntervalRequest",
    # Site Management
    "NavigationItemBase",
    "NavigationItemCreate",
    "NavigationItemUpdate",
    "NavigationItemResponse",
    "NavigationTreeResponse",
    "NavigationItemListResponse",
    "NavigationSortItem",
    "NavigationSortRequest",
    "SiteConfigBase",
    "SiteConfigCreate",
    "SiteConfigUpdate",
    "SiteConfigResponse",
    "SiteConfigListResponse",
    "BulkOperationRequest",
    "BulkOperationResponse",
    "DefaultNavigationData",
    # AI
    "ParsedSearchIntent",
    "NaturalSearchRequest",
    "AttachmentInfo",
    "DocumentSearchResult",
    "NaturalSearchResponse",
]
