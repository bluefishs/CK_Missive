# -*- coding: utf-8 -*-
"""
API 回應輔助模組

提供統一的 API 回應格式轉換功能。
將服務層的 ServiceResponse 轉換為 FastAPI JSONResponse。
"""
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse
from fastapi import status as http_status

from app.services.base.response import ServiceResponse, ImportResult


def service_response_to_json(
    response: ServiceResponse,
    success_status: int = http_status.HTTP_200_OK,
    error_status: int = http_status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """
    將 ServiceResponse 轉換為 JSONResponse

    Args:
        response: ServiceResponse 物件
        success_status: 成功時的 HTTP 狀態碼
        error_status: 失敗時的 HTTP 狀態碼

    Returns:
        JSONResponse
    """
    status_code = success_status if response.success else error_status
    return JSONResponse(
        content=response.to_dict(),
        status_code=status_code
    )


def import_result_to_json(
    result: ImportResult,
    success_status: int = http_status.HTTP_200_OK,
    error_status: int = http_status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """
    將 ImportResult 轉換為 JSONResponse

    Args:
        result: ImportResult 物件
        success_status: 成功時的 HTTP 狀態碼
        error_status: 失敗時的 HTTP 狀態碼

    Returns:
        JSONResponse
    """
    status_code = success_status if result.success else error_status
    return JSONResponse(
        content=result.to_dict(),
        status_code=status_code
    )


def success_response(
    data: Any = None,
    message: str = "操作成功",
    code: str = "OK"
) -> Dict[str, Any]:
    """
    建立成功回應字典

    Args:
        data: 回應資料
        message: 訊息
        code: 狀態碼

    Returns:
        回應字典
    """
    return {
        "success": True,
        "data": data,
        "message": message,
        "code": code,
        "errors": [],
        "warnings": []
    }


def error_response(
    message: str,
    code: str = "ERROR",
    errors: Optional[list] = None,
    status_code: int = http_status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """
    建立錯誤回應

    Args:
        message: 錯誤訊息
        code: 錯誤代碼
        errors: 詳細錯誤列表
        status_code: HTTP 狀態碼

    Returns:
        JSONResponse
    """
    return JSONResponse(
        content={
            "success": False,
            "data": None,
            "message": message,
            "code": code,
            "errors": errors or [],
            "warnings": []
        },
        status_code=status_code
    )


def validation_error_response(
    errors: list,
    message: str = "資料驗證失敗"
) -> JSONResponse:
    """
    建立驗證錯誤回應

    Args:
        errors: 驗證錯誤列表
        message: 錯誤訊息

    Returns:
        JSONResponse
    """
    return error_response(
        message=message,
        code="VALIDATION_ERROR",
        errors=errors,
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY
    )


def not_found_response(
    resource: str = "資源",
    message: Optional[str] = None
) -> JSONResponse:
    """
    建立 404 回應

    Args:
        resource: 資源名稱
        message: 自訂訊息

    Returns:
        JSONResponse
    """
    return error_response(
        message=message or f"{resource}不存在",
        code="NOT_FOUND",
        status_code=http_status.HTTP_404_NOT_FOUND
    )


# 錯誤代碼對應 HTTP 狀態碼
ERROR_CODE_STATUS_MAP = {
    "OK": http_status.HTTP_200_OK,
    "CREATED": http_status.HTTP_201_CREATED,
    "PARTIAL": http_status.HTTP_200_OK,
    "VALIDATION_ERROR": http_status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_FOUND": http_status.HTTP_404_NOT_FOUND,
    "DUPLICATE_ERROR": http_status.HTTP_409_CONFLICT,
    "IMPORT_ERROR": http_status.HTTP_400_BAD_REQUEST,
    "EXPORT_ERROR": http_status.HTTP_500_INTERNAL_SERVER_ERROR,
    "DATABASE_ERROR": http_status.HTTP_500_INTERNAL_SERVER_ERROR,
    "UNKNOWN_ERROR": http_status.HTTP_500_INTERNAL_SERVER_ERROR,
    "ERROR": http_status.HTTP_400_BAD_REQUEST,
}


def get_status_code_for_error(code: str) -> int:
    """
    根據錯誤代碼取得對應的 HTTP 狀態碼

    Args:
        code: 錯誤代碼

    Returns:
        HTTP 狀態碼
    """
    return ERROR_CODE_STATUS_MAP.get(code, http_status.HTTP_400_BAD_REQUEST)
