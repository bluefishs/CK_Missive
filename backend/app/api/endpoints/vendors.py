"""
協力廠商管理 API 端點

使用統一回應格式與異常處理機制
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, Body
from pydantic import Field

from app.extended.models import User
from app.core.dependencies import require_auth, require_permission
from app.schemas.vendor import (
    Vendor, VendorCreate, VendorUpdate,
    VendorListQuery, VendorStatisticsResponse
)
from app.schemas.common import (
    PaginatedResponse,
    PaginationMeta,
    DeleteResponse,
    BaseQueryParams,
)
from app.services.vendor_service import VendorService
from app.core.exceptions import NotFoundException, ConflictException, ResourceInUseException
from app.core.dependencies import get_service

router = APIRouter()


# 注意：VendorListQuery, VendorStatisticsResponse 已統一定義於 app/schemas/vendor.py


# ============================================================================
# 回應格式 Schema (保留 VendorListResponse 作為統一分頁格式)
# ============================================================================

class VendorListResponse(PaginatedResponse):
    """廠商列表回應（使用統一分頁格式）"""
    items: list[Vendor] = Field(default=[], description="廠商列表")


# ============================================================================
# API 端點
# ============================================================================

@router.post(
    "/list",
    response_model=VendorListResponse,
    summary="查詢廠商列表",
    description="取得廠商列表，支援分頁、搜尋和篩選"
)
async def list_vendors(
    query: VendorListQuery = Body(default=VendorListQuery()),
    vendor_service: VendorService = Depends(get_service(VendorService)),
    current_user: User = Depends(require_auth())
):
    """
    查詢廠商列表

    - 支援分頁（page, limit）
    - 支援搜尋（search: 廠商名稱、代碼、聯絡人）
    - 支援排序（sort_by, sort_order）
    - 需要認證
    """
    skip = (query.page - 1) * query.limit if query.page else 0

    vendors = await vendor_service.get_vendors(
        skip=skip,
        limit=query.limit,
        search=query.search,
        business_type=query.business_type,
        rating=query.rating
    )
    total = await vendor_service.get_total_vendors(
        search=query.search,
        business_type=query.business_type,
        rating=query.rating
    )

    return VendorListResponse(
        items=vendors,
        pagination=PaginationMeta.create(
            total=total,
            page=query.page,
            limit=query.limit
        )
    )


@router.post(
    "",
    response_model=Vendor,
    status_code=status.HTTP_201_CREATED,
    summary="建立新廠商"
)
async def create_vendor(
    vendor: VendorCreate,
    vendor_service: VendorService = Depends(get_service(VendorService)),
    current_user: User = Depends(require_permission("vendors:create"))
):
    """
    建立新廠商

    🔒 權限要求：vendors:create
    若廠商代碼已存在會回傳 409 Conflict 錯誤。
    """
    try:
        return await vendor_service.create_vendor(vendor)
    except ValueError as e:
        raise ConflictException(
            message=str(e),
            field="vendor_code",
            value=vendor.vendor_code
        )


@router.post(
    "/{vendor_id}/detail",
    response_model=Vendor,
    summary="取得廠商詳情"
)
async def get_vendor_detail(
    vendor_id: int,
    vendor_service: VendorService = Depends(get_service(VendorService)),
    current_user: User = Depends(require_auth())
):
    """
    取得單一廠商詳情

    🔒 需要認證。若找不到廠商會回傳 404 Not Found 錯誤。
    """
    db_vendor = await vendor_service.get_vendor(vendor_id)
    if not db_vendor:
        raise NotFoundException(resource="廠商", resource_id=vendor_id)
    return db_vendor


@router.post(
    "/{vendor_id}/update",
    response_model=Vendor,
    summary="更新廠商"
)
async def update_vendor(
    vendor_id: int,
    vendor: VendorUpdate,
    vendor_service: VendorService = Depends(get_service(VendorService)),
    current_user: User = Depends(require_permission("vendors:edit"))
):
    """
    更新廠商資料

    🔒 權限要求：vendors:edit
    若找不到廠商會回傳 404 Not Found 錯誤。
    """
    updated_vendor = await vendor_service.update_vendor(vendor_id, vendor)
    if not updated_vendor:
        raise NotFoundException(resource="廠商", resource_id=vendor_id)
    return updated_vendor


@router.post(
    "/{vendor_id}/delete",
    response_model=DeleteResponse,
    summary="刪除廠商"
)
async def delete_vendor(
    vendor_id: int,
    vendor_service: VendorService = Depends(get_service(VendorService)),
    current_user: User = Depends(require_permission("vendors:delete"))
):
    """
    刪除廠商

    🔒 權限要求：vendors:delete
    - 若找不到廠商會回傳 404 Not Found 錯誤
    - 若廠商與專案有關聯會回傳 409 Conflict 錯誤
    """
    try:
        success = await vendor_service.delete_vendor(vendor_id)
        if not success:
            raise NotFoundException(resource="廠商", resource_id=vendor_id)
        return DeleteResponse(
            success=True,
            message="廠商已成功刪除",
            deleted_id=vendor_id
        )
    except ValueError as e:
        raise ResourceInUseException(
            resource="廠商",
            reason=str(e)
        )


@router.post(
    "/statistics",
    response_model=VendorStatisticsResponse,
    summary="取得廠商統計"
)
async def get_vendor_statistics(
    vendor_service: VendorService = Depends(get_service(VendorService)),
    current_user: User = Depends(require_auth())
):
    """
    取得廠商統計資料

    🔒 需要認證
    包含：
    - 總廠商數
    - 按業務類型分組統計
    - 按評等分組統計
    """
    stats = await vendor_service.get_vendor_statistics()
    return VendorStatisticsResponse(success=True, data=stats)


# ============================================================================
# 相容性端點（供前端下拉選單使用，將逐步淘汰）
# ============================================================================

@router.post(
    "",
    response_model=dict,
    summary="[相容] 取得廠商列表 (預計 2026-07 移除)",
    deprecated=True
)
async def list_vendors_legacy(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    vendor_service: VendorService = Depends(get_service(VendorService)),
    current_user: User = Depends(require_auth())
):
    """
    [相容性端點] 取得廠商列表

    ⚠️ **預計廢止日期**: 2026-07
    此端點為向後相容保留，請改用 POST /vendors/list
    需要認證。
    """
    vendors = await vendor_service.get_vendors(skip, limit, search)
    total = await vendor_service.get_total_vendors(search)
    return {"vendors": vendors, "total": total}
