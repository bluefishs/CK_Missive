#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依賴注入模組

提供統一的依賴注入機制，用於 FastAPI 端點。
使用工廠函數模式，確保 Service 實例正確接收資料庫 session。
"""

from typing import Type, TypeVar, Callable, Any
from functools import wraps
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db

# 泛型類型變數
T = TypeVar('T')


# ============================================================================
# Service 工廠函數
# ============================================================================

def get_service(service_class: Type[T]) -> Callable[[AsyncSession], T]:
    """
    建立 Service 依賴注入工廠函數

    使用方式:
        from app.core.dependencies import get_service
        from app.services.vendor_service import VendorService

        @router.get("/vendors")
        async def list_vendors(
            vendor_service: VendorService = Depends(get_service(VendorService))
        ):
            return await vendor_service.get_vendors()

    Args:
        service_class: Service 類別

    Returns:
        依賴注入函數
    """
    def _get_service(db: AsyncSession = Depends(get_async_db)) -> T:
        # 建立 Service 實例並傳入 db session
        return service_class(db)
    return _get_service


# ============================================================================
# 預設的 Service 依賴函數（無 session 注入的 Service）
# ============================================================================

# 這些 Service 不需要在建構函數接收 db，而是在方法中接收
# 保持向後相容性

from app.services.vendor_service import VendorService
from app.services.project_service import ProjectService
from app.services.agency_service import AgencyService
from app.services.document_service import DocumentService


def get_vendor_service() -> VendorService:
    """取得 VendorService 實例"""
    return VendorService()


def get_project_service() -> ProjectService:
    """取得 ProjectService 實例"""
    return ProjectService()


def get_agency_service() -> AgencyService:
    """取得 AgencyService 實例"""
    return AgencyService()


def get_document_service() -> DocumentService:
    """取得 DocumentService 實例"""
    return DocumentService()


# ============================================================================
# 分頁參數依賴
# ============================================================================

from app.schemas.common import PaginationParams, BaseQueryParams


async def get_pagination(
    page: int = 1,
    limit: int = 20
) -> PaginationParams:
    """
    分頁參數依賴注入

    使用方式:
        @router.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends(get_pagination)
        ):
            skip = pagination.skip
            limit = pagination.limit
    """
    return PaginationParams(page=page, limit=limit)


async def get_query_params(
    page: int = 1,
    limit: int = 20,
    search: str = None,
    sort_by: str = "id",
    sort_order: str = "desc"
) -> BaseQueryParams:
    """
    通用查詢參數依賴注入

    包含分頁、搜尋和排序參數。
    """
    from app.schemas.common import SortOrder
    return BaseQueryParams(
        page=page,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=SortOrder(sort_order) if sort_order in ['asc', 'desc'] else SortOrder.DESC
    )


# ============================================================================
# 認證與權限依賴
# ============================================================================

from app.extended.models import User
from app.api.endpoints.auth import get_current_user


def require_auth() -> Callable:
    """
    需要認證的依賴

    使用方式:
        @router.get("/protected")
        async def protected_endpoint(
            current_user: User = Depends(require_auth())
        ):
            return {"user": current_user.username}
    """
    return get_current_user


def optional_auth() -> Callable:
    """
    可選認證的依賴

    若有 token 則驗證並返回用戶，無 token 則返回 None
    注意：需要在 auth.py 中實作 get_current_user_optional
    """
    # TODO: 待實作 get_current_user_optional
    return get_current_user


def require_admin():
    """
    需要管理員權限的依賴

    使用方式:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: User = Depends(require_admin())
        ):
            return {"message": "Admin access granted"}
    """
    async def _require_admin(
        current_user: User = Depends(get_current_user)
    ) -> User:
        from app.core.exceptions import ForbiddenException
        if not current_user.is_admin and not current_user.is_superuser:
            raise ForbiddenException("需要管理員權限")
        return current_user
    return _require_admin


def require_permission(permission: str):
    """
    需要特定權限的依賴

    使用方式:
        @router.delete("/items/{id}")
        async def delete_item(
            id: int,
            current_user: User = Depends(require_permission("items:delete"))
        ):
            pass

    Args:
        permission: 需要的權限名稱
    """
    async def _require_permission(
        current_user: User = Depends(get_current_user)
    ) -> User:
        from app.core.exceptions import ForbiddenException
        from app.core.auth_service import AuthService

        # 超級管理員擁有所有權限
        if current_user.is_superuser:
            return current_user

        # 檢查特定權限
        if not AuthService.check_permission(current_user, permission):
            raise ForbiddenException(f"需要 '{permission}' 權限")

        return current_user
    return _require_permission


# ============================================================================
# 快取相關依賴（預留）
# ============================================================================

# async def get_cache_manager():
#     """取得快取管理器"""
#     from app.core.cache_manager import cache_manager
#     return cache_manager
