"""
公文管理 API 共用模組

包含所有子模組共用的導入、模型和工具函數

@version 3.0.0
@date 2026-01-18
"""
import logging
from typing import Optional
from datetime import date as date_type
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import (
    OfficialDocument,
    ContractProject,
    GovernmentAgency,
    DocumentAttachment,
    User,
    project_user_assignment,
)
from app.services.document_service import DocumentService
from app.services.document_statistics_service import DocumentStatisticsService
from app.services.document_export_service import DocumentExportService
from app.schemas.document import (
    DocumentFilter,
    DocumentListQuery,
    DocumentListResponse,
    DocumentResponse,
    StaffInfo,
    DocumentCreateRequest,
    DocumentUpdateRequest,
    VALID_DOC_TYPES,
)
from app.schemas.common import (
    PaginationMeta,
    DeleteResponse,
    SuccessResponse,
    SortOrder,
)
from app.schemas.document_query import (
    DropdownQuery,
    AgencyDropdownQuery,
    OptimizedSearchRequest,
    SearchSuggestionRequest,
    AuditLogQuery,
    AuditLogItem,
    AuditLogResponse,
    ProjectDocumentsQuery,
    DocumentExportQuery,
    ExcelExportRequest,
)
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.rls_filter import RLSFilter
from app.core.audit_logger import DocumentUpdateGuard
from app.services.notification_service import NotificationService, CRITICAL_FIELDS
from app.core.dependencies import require_auth, require_permission, get_service
from app.api.endpoints.auth import get_current_user

# 依賴注入工廠函數
get_document_service = get_service(DocumentService)
get_statistics_service = get_service(DocumentStatisticsService)
get_export_service = get_service(DocumentExportService)

logger = logging.getLogger(__name__)

# HTTP Bearer 認證
security = HTTPBearer(auto_error=False)


def parse_date_string(date_str: Optional[str]) -> Optional[date_type]:
    """將日期字串轉換為 Python date 物件"""
    if not date_str:
        return None
    try:
        parts = date_str.split('-')
        if len(parts) == 3:
            return date_type(int(parts[0]), int(parts[1]), int(parts[2]))
        return None
    except (ValueError, IndexError):
        logger.warning(f"無法解析日期字串: {date_str}")
        return None


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> Optional[User]:
    """取得當前使用者（可選，不強制認證）- 僅用於向後相容"""
    try:
        if not credentials:
            return None
        return await get_current_user(credentials, db)
    except Exception:
        return None


def extract_agency_names_from_raw(raw_value: str) -> list:
    """從原始值中提取機關名稱列表"""
    if not raw_value:
        return []

    # 處理可能的 JSON 格式
    if raw_value.startswith('['):
        import json
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            pass

    # 分割字串
    separators = ['、', ',', '；', ';']
    names = [raw_value]
    for sep in separators:
        new_names = []
        for name in names:
            new_names.extend(name.split(sep))
        names = new_names

    return [name.strip() for name in names if name.strip()]


# 匯出所有共用元素
__all__ = [
    # Logger
    "logger",
    # FastAPI
    "Depends",
    "security",
    # SQLAlchemy
    "AsyncSession",
    # 資料庫
    "get_async_db",
    # Models
    "OfficialDocument",
    "ContractProject",
    "GovernmentAgency",
    "DocumentAttachment",
    "User",
    "project_user_assignment",
    # Services
    "DocumentService",
    "DocumentStatisticsService",
    "DocumentExportService",
    "NotificationService",
    "CRITICAL_FIELDS",
    # Dependencies
    "get_document_service",
    "get_statistics_service",
    "get_export_service",
    # Schemas - Document
    "DocumentFilter",
    "DocumentListQuery",
    "DocumentListResponse",
    "DocumentResponse",
    "StaffInfo",
    "DocumentCreateRequest",
    "DocumentUpdateRequest",
    "VALID_DOC_TYPES",
    # Schemas - Common
    "PaginationMeta",
    "DeleteResponse",
    "SuccessResponse",
    "SortOrder",
    # Schemas - Query
    "DropdownQuery",
    "AgencyDropdownQuery",
    "OptimizedSearchRequest",
    "SearchSuggestionRequest",
    "AuditLogQuery",
    "AuditLogItem",
    "AuditLogResponse",
    "ProjectDocumentsQuery",
    "DocumentExportQuery",
    "ExcelExportRequest",
    # Exceptions
    "NotFoundException",
    "ForbiddenException",
    # Core
    "RLSFilter",
    "DocumentUpdateGuard",
    "require_auth",
    "require_permission",
    "get_current_user",
    # Utilities
    "parse_date_string",
    "get_optional_user",
    "extract_agency_names_from_raw",
]
