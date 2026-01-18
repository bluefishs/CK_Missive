#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一異常定義與處理

此模組定義了系統的自定義異常類別和統一的異常處理器。
所有 API 異常都應使用這些類別以確保回應格式一致。
"""

from typing import Optional, List, Any, Dict
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from datetime import datetime
import logging

from app.schemas.common import ErrorCode, ErrorDetail
from app.core.cors import allowed_origins

logger = logging.getLogger(__name__)


# ============================================================================
# 自定義異常基類
# ============================================================================

class AppException(Exception):
    """
    應用程式異常基類

    所有自定義異常都應繼承此類。
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[List[ErrorDetail]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        error_dict = {
            "code": self.code.value,
            "message": self.message
        }
        if self.details:
            error_dict["details"] = [d.model_dump() for d in self.details]
        return error_dict


# ============================================================================
# 具體異常類
# ============================================================================

class ValidationException(AppException):
    """驗證異常"""

    def __init__(
        self,
        message: str = "輸入資料驗證失敗",
        details: Optional[List[ErrorDetail]] = None
    ):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class NotFoundException(AppException):
    """資源不存在異常"""

    def __init__(
        self,
        resource: str = "資源",
        resource_id: Optional[Any] = None
    ):
        message = f"{resource}不存在"
        if resource_id:
            message = f"{resource} (ID: {resource_id}) 不存在"
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


class UnauthorizedException(AppException):
    """未授權異常"""

    def __init__(self, message: str = "請先登入"):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenException(AppException):
    """權限不足異常"""

    def __init__(self, message: str = "您沒有權限執行此操作"):
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class ConflictException(AppException):
    """資源衝突異常"""

    def __init__(
        self,
        message: str = "資源衝突",
        field: Optional[str] = None,
        value: Optional[Any] = None
    ):
        details = []
        if field:
            details.append(ErrorDetail(field=field, message=message, value=value))
        super().__init__(
            code=ErrorCode.CONFLICT,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class DuplicateException(AppException):
    """重複資料異常"""

    def __init__(
        self,
        field: str,
        value: Any,
        message: Optional[str] = None
    ):
        msg = message or f"'{field}' 的值 '{value}' 已存在"
        super().__init__(
            code=ErrorCode.DUPLICATE_ENTRY,
            message=msg,
            status_code=status.HTTP_409_CONFLICT,
            details=[ErrorDetail(field=field, message=msg, value=value)]
        )


class ResourceInUseException(AppException):
    """資源使用中異常"""

    def __init__(
        self,
        resource: str,
        reason: Optional[str] = None
    ):
        message = f"{resource}正在被使用中，無法刪除"
        if reason:
            message = f"{message}。原因：{reason}"
        super().__init__(
            code=ErrorCode.RESOURCE_IN_USE,
            message=message,
            status_code=status.HTTP_409_CONFLICT
        )


class InvalidOperationException(AppException):
    """無效操作異常"""

    def __init__(self, message: str = "無法執行此操作"):
        super().__init__(
            code=ErrorCode.INVALID_OPERATION,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class DatabaseException(AppException):
    """資料庫異常"""

    def __init__(self, message: str = "資料庫操作失敗"):
        super().__init__(
            code=ErrorCode.DATABASE_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class InternalException(AppException):
    """內部錯誤異常"""

    def __init__(self, message: str = "伺服器內部錯誤"):
        super().__init__(
            code=ErrorCode.INTERNAL_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# 統一錯誤回應格式化
# ============================================================================

def format_error_response(
    code: ErrorCode,
    message: str,
    details: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    格式化錯誤回應

    Args:
        code: 錯誤碼
        message: 錯誤訊息
        details: 錯誤詳細資訊

    Returns:
        標準化的錯誤回應字典
    """
    response = {
        "success": False,
        "error": {
            "code": code.value,
            "message": message
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    if details:
        response["error"]["details"] = details
    return response


# ============================================================================
# 異常處理器
# ============================================================================

def _get_cors_headers(request: Request) -> dict:
    """取得 CORS 標頭，確保錯誤回應也包含正確的 CORS 設定"""
    origin = request.headers.get("origin", "")
    
    # 從 app.core.cors 模組導入統一的 allowed_origins
    if origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        }
    return {}


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    自定義異常處理器

    處理所有 AppException 及其子類的異常。
    """
    logger.warning(
        f"AppException: {exc.code.value} - {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.code.value
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            code=exc.code,
            message=exc.message,
            details=[d.model_dump() for d in exc.details] if exc.details else None
        ),
        headers=_get_cors_headers(request)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP 異常處理器

    將 FastAPI 的 HTTPException 轉換為統一格式。
    """
    # 根據狀態碼映射錯誤碼
    code_mapping = {
        400: ErrorCode.BAD_REQUEST,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
        500: ErrorCode.INTERNAL_ERROR,
    }
    code = code_mapping.get(exc.status_code, ErrorCode.INTERNAL_ERROR)

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            code=code,
            message=str(exc.detail)
        ),
        headers=_get_cors_headers(request)
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Pydantic 驗證異常處理器

    將 Pydantic 的驗證錯誤轉換為統一格式。
    """
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details.append({
            "field": field,
            "message": error["msg"],
            "value": error.get("input")
        })

    logger.warning(
        f"Validation error on {request.url.path}",
        extra={"errors": details}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="輸入資料驗證失敗",
            details=details
        ),
        headers=_get_cors_headers(request)
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    通用異常處理器

    處理所有未捕獲的異常，記錄錯誤並返回統一格式。
    """
    logger.exception(
        f"Unhandled exception on {request.url.path}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="伺服器發生未預期的錯誤，請稍後再試"
        ),
        headers=_get_cors_headers(request)
    )


# ============================================================================
# 註冊異常處理器的輔助函數
# ============================================================================

def register_exception_handlers(app):
    """
    註冊所有異常處理器到 FastAPI 應用程式

    Args:
        app: FastAPI 應用程式實例
    """
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # 啟用通用異常處理器以確保 CORS headers 正確返回
    app.add_exception_handler(Exception, generic_exception_handler)
