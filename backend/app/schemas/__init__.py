#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schemas 模組匯出

統一匯出所有 Pydantic Schema 定義。
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
from app.schemas.auth import *

# 公文相關
from app.schemas.document import *

# 專案相關
from app.schemas.project import *

# 廠商相關
from app.schemas.vendor import *

# 機關相關
from app.schemas.agency import *

# 專案廠商關聯
from app.schemas.project_vendor import *

# 專案人員關聯
from app.schemas.project_staff import *

# 行事曆相關 (calendar.py 已歸檔至 _archived，使用 document_calendar.py)
from app.schemas.document_calendar import *

# 網站管理
from app.schemas.site_management import *

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
]
