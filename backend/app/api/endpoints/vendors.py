"""
協力廠商管理 API 端點

使用統一回應格式與異常處理機制
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.database import get_async_db
from app.extended.models import User
from app.api.endpoints.auth import get_current_user
from app.core.dependencies import require_auth
from app.schemas.vendor import Vendor, VendorCreate, VendorUpdate
from app.schemas.common import (
    PaginatedResponse,
    PaginationMeta,
    DeleteResponse,
    BaseQueryParams,
)
from app.services.vendor_service import VendorService
from app.core.exceptions import NotFoundException, ConflictException, ResourceInUseException

router = APIRouter()
vendor_service = VendorService()


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class VendorListQuery(BaseQueryParams):
    """廠商列表查詢參數"""
    business_type: Optional[str] = Field(None, description="業務類型篩選")


# ============================================================================
# 回應格式 Schema
# ============================================================================

class VendorListResponse(PaginatedResponse):
    """廠商列表回應（使用統一分頁格式）"""
    items: list[Vendor] = Field(default=[], description="廠商列表")


class VendorStatisticsResponse(BaseModel):
    """廠商統計回應"""
    success: bool = True
    data: dict = Field(..., description="統計資料")


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
    db: AsyncSession = Depends(get_async_db),
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
        db,
        skip=skip,
        limit=query.limit,
        search=query.search
    )
    total = await vendor_service.get_total_vendors(db, search=query.search)

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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    建立新廠商

    需要認證。若廠商代碼已存在會回傳 409 Conflict 錯誤。
    """
    try:
        return await vendor_service.create_vendor(db, vendor)
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    取得單一廠商詳情

    需要認證。若找不到廠商會回傳 404 Not Found 錯誤。
    """
    db_vendor = await vendor_service.get_vendor(db, vendor_id)
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新廠商資料

    需要認證。若找不到廠商會回傳 404 Not Found 錯誤。
    """
    updated_vendor = await vendor_service.update_vendor(db, vendor_id, vendor)
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    刪除廠商

    需要認證。
    - 若找不到廠商會回傳 404 Not Found 錯誤
    - 若廠商與專案有關聯會回傳 409 Conflict 錯誤
    """
    try:
        success = await vendor_service.delete_vendor(db, vendor_id)
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    取得廠商統計資料

    包含：
    - 總廠商數
    - 按業務類型分組統計
    - 按評等分組統計
    """
    stats = await vendor_service.get_vendor_statistics(db)
    return VendorStatisticsResponse(success=True, data=stats)


# ============================================================================
# 相容性端點（供前端下拉選單使用，將逐步淘汰）
# ============================================================================

@router.get(
    "",
    response_model=dict,
    summary="[相容] 取得廠商列表",
    deprecated=True
)
async def list_vendors_legacy(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    [相容性端點] 取得廠商列表

    此端點為向後相容保留，請改用 POST /vendors/list
    需要認證。
    """
    vendors = await vendor_service.get_vendors(db, skip, limit, search)
    total = await vendor_service.get_total_vendors(db, search)
    return {"vendors": vendors, "total": total}
