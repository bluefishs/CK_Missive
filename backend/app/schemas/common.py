#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一回應格式與通用 Schema 定義

此模組定義了系統所有 API 回應的統一格式，確保前後端一致性。
所有 API 端點都應使用這些通用 Schema 作為回應格式。
"""

from typing import TypeVar, Generic, Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

# 泛型類型變數
T = TypeVar('T')


# ============================================================================
# 錯誤碼定義
# ============================================================================

class ErrorCode(str, Enum):
    """統一錯誤碼定義"""
    # 驗證錯誤 (4xx)
    VALIDATION_ERROR = "ERR_VALIDATION"
    NOT_FOUND = "ERR_NOT_FOUND"
    UNAUTHORIZED = "ERR_UNAUTHORIZED"
    FORBIDDEN = "ERR_FORBIDDEN"
    CONFLICT = "ERR_CONFLICT"
    BAD_REQUEST = "ERR_BAD_REQUEST"

    # 伺服器錯誤 (5xx)
    INTERNAL_ERROR = "ERR_INTERNAL"
    DATABASE_ERROR = "ERR_DATABASE"
    SERVICE_UNAVAILABLE = "ERR_SERVICE_UNAVAILABLE"

    # 業務邏輯錯誤
    DUPLICATE_ENTRY = "ERR_DUPLICATE"
    INVALID_OPERATION = "ERR_INVALID_OPERATION"
    RESOURCE_IN_USE = "ERR_RESOURCE_IN_USE"


# ============================================================================
# 錯誤回應格式
# ============================================================================

class ErrorDetail(BaseModel):
    """錯誤詳細資訊"""
    field: Optional[str] = Field(None, description="發生錯誤的欄位名稱")
    message: str = Field(..., description="錯誤訊息")
    value: Optional[Any] = Field(None, description="導致錯誤的值")


class ErrorResponse(BaseModel):
    """
    統一錯誤回應格式

    所有 API 錯誤回應都應使用此格式。

    Example:
        {
            "success": false,
            "error": {
                "code": "ERR_VALIDATION",
                "message": "輸入資料驗證失敗",
                "details": [
                    {"field": "email", "message": "電子郵件格式不正確", "value": "invalid"}
                ]
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }
    """
    success: bool = Field(default=False, description="操作是否成功")
    error: Dict[str, Any] = Field(..., description="錯誤資訊")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="錯誤發生時間")

    @classmethod
    def create(
        cls,
        code: ErrorCode,
        message: str,
        details: Optional[List[ErrorDetail]] = None
    ) -> "ErrorResponse":
        """建立錯誤回應"""
        error_dict = {
            "code": code.value,
            "message": message
        }
        if details:
            error_dict["details"] = [d.model_dump() for d in details]
        return cls(error=error_dict)


# ============================================================================
# 成功回應格式
# ============================================================================

class SuccessResponse(BaseModel, Generic[T]):
    """
    統一成功回應格式（單一資料）

    Example:
        {
            "success": true,
            "data": { ... },
            "message": "操作成功"
        }
    """
    success: bool = Field(default=True, description="操作是否成功")
    data: Optional[T] = Field(None, description="回應資料")
    message: Optional[str] = Field(None, description="操作訊息")


# ============================================================================
# 分頁相關
# ============================================================================

class PaginationParams(BaseModel):
    """
    分頁參數

    用於 API 請求中的分頁控制。
    """
    page: int = Field(default=1, ge=1, description="頁碼（從1開始）")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數（最大100）")

    @property
    def skip(self) -> int:
        """計算跳過的筆數"""
        return (self.page - 1) * self.limit


class PaginationMeta(BaseModel):
    """
    分頁元資料

    包含在分頁回應中，提供分頁狀態資訊。
    """
    total: int = Field(..., ge=0, description="總筆數")
    page: int = Field(..., ge=1, description="當前頁碼")
    limit: int = Field(..., ge=1, description="每頁筆數")
    total_pages: int = Field(..., ge=0, description="總頁數")
    has_next: bool = Field(..., description="是否有下一頁")
    has_prev: bool = Field(..., description="是否有上一頁")

    @classmethod
    def create(cls, total: int, page: int, limit: int) -> "PaginationMeta":
        """根據總數、頁碼、每頁筆數建立分頁元資料"""
        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    統一分頁回應格式

    所有列表 API 都應使用此格式回應。

    Example:
        {
            "success": true,
            "items": [...],
            "pagination": {
                "total": 100,
                "page": 1,
                "limit": 20,
                "total_pages": 5,
                "has_next": true,
                "has_prev": false
            }
        }
    """
    success: bool = Field(default=True, description="操作是否成功")
    items: List[T] = Field(default=[], description="資料列表")
    pagination: PaginationMeta = Field(..., description="分頁資訊")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        limit: int
    ) -> "PaginatedResponse[T]":
        """建立分頁回應"""
        return cls(
            items=items,
            pagination=PaginationMeta.create(total, page, limit)
        )


# ============================================================================
# 排序相關
# ============================================================================

class SortOrder(str, Enum):
    """排序方向"""
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    """排序參數"""
    sort_by: Optional[str] = Field(default="id", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="排序方向")


# ============================================================================
# 查詢參數基類
# ============================================================================

class BaseQueryParams(PaginationParams, SortParams):
    """
    基礎查詢參數

    包含分頁和排序功能，可被各模組的查詢參數繼承。
    """
    search: Optional[str] = Field(None, description="搜尋關鍵字")


# ============================================================================
# 通用回應
# ============================================================================

class DeleteResponse(BaseModel):
    """刪除操作回應"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="刪除成功", description="操作訊息")
    deleted_id: int = Field(..., description="被刪除的資源 ID")


class BatchOperationResponse(BaseModel):
    """批次操作回應"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(..., description="操作訊息")
    success_count: int = Field(default=0, description="成功數量")
    failed_count: int = Field(default=0, description="失敗數量")
    failed_ids: List[int] = Field(default=[], description="失敗的 ID 列表")
    errors: List[str] = Field(default=[], description="錯誤訊息列表")


# ============================================================================
# 健康檢查
# ============================================================================

class HealthStatus(str, Enum):
    """健康狀態"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthCheckResponse(BaseModel):
    """健康檢查回應"""
    status: HealthStatus = Field(..., description="服務狀態")
    version: str = Field(..., description="API 版本")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="檢查時間")
    services: Dict[str, HealthStatus] = Field(default={}, description="各服務狀態")


# ============================================================================
# 下拉選項格式
# ============================================================================

class SelectOption(BaseModel):
    """通用下拉選項格式"""
    value: Any = Field(..., description="選項值")
    label: str = Field(..., description="顯示文字")
    disabled: bool = Field(default=False, description="是否禁用")

    model_config = ConfigDict(from_attributes=True)


class SelectOptionInt(BaseModel):
    """整數值下拉選項"""
    value: int = Field(..., description="選項值")
    label: str = Field(..., description="顯示文字")

    model_config = ConfigDict(from_attributes=True)


class SelectOptionStr(BaseModel):
    """字串值下拉選項"""
    value: str = Field(..., description="選項值")
    label: str = Field(..., description="顯示文字")

    model_config = ConfigDict(from_attributes=True)
