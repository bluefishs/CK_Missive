"""
機關單位管理 API 端點 - POST-only 資安機制，統一回應格式
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.extended.models import User
from app.schemas.agency import (
    Agency, AgencyCreate, AgencyUpdate, AgencyWithStats,
    AgenciesResponse, AgencyStatistics
)
from app.schemas.common import PaginationMeta, SortOrder
from app.services.agency_service import AgencyService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class AgencyListQuery(BaseModel):
    """機關列表查詢參數（統一格式）"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=1000, description="每頁筆數")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    agency_type: Optional[str] = Field(None, description="機關類型")
    include_stats: bool = Field(default=True, description="是否包含統計資料")
    sort_by: str = Field(default="agency_name", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.ASC, description="排序方向")


class AgencyListResponse(BaseModel):
    """機關列表回應 Schema（統一分頁格式）"""
    success: bool = True
    items: List[AgencyWithStats] = Field(default=[], description="機關列表")
    pagination: PaginationMeta


# ============================================================================
# 機關列表 API（POST-only 資安機制）
# ============================================================================

@router.post(
    "/list",
    response_model=AgencyListResponse,
    summary="查詢機關列表",
    description="使用統一分頁格式查詢機關列表（POST-only 資安機制）"
)
async def list_agencies(
    query: AgencyListQuery = Body(default=AgencyListQuery()),
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends()
):
    """
    查詢機關列表（POST-only 資安機制）

    回應格式：
    ```json
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
    ```
    """
    try:
        skip = (query.page - 1) * query.limit

        if query.include_stats:
            result = await agency_service.get_agencies_with_stats(
                db, skip=skip, limit=query.limit, search=query.search
            )
            items = result["agencies"]
            total = result["total"]
        else:
            items = await agency_service.get_agencies(
                db, skip=skip, limit=query.limit
            )
            total = len(items)

        return AgencyListResponse(
            success=True,
            items=items,
            pagination=PaginationMeta.create(
                total=total,
                page=query.page,
                limit=query.limit
            )
        )
    except Exception as e:
        logger.error(f"查詢機關列表失敗: {e}", exc_info=True)
        return AgencyListResponse(
            success=False,
            items=[],
            pagination=PaginationMeta.create(total=0, page=1, limit=query.limit)
        )


@router.post(
    "/{agency_id}/detail",
    response_model=Agency,
    summary="取得機關詳情"
)
async def get_agency_detail(
    agency_id: int,
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends()
):
    """取得單一機關詳情"""
    agency = await agency_service.get_agency(db, agency_id=agency_id)
    if agency is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到指定的機關單位"
        )
    return agency


@router.post(
    "",
    response_model=Agency,
    status_code=status.HTTP_201_CREATED,
    summary="建立機關"
)
async def create_agency(
    agency: AgencyCreate = Body(...),
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends()
):
    """建立新機關單位"""
    try:
        return await agency_service.create_agency(db=db, agency=agency)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post(
    "/{agency_id}/update",
    response_model=Agency,
    summary="更新機關"
)
async def update_agency(
    agency_id: int,
    agency: AgencyUpdate = Body(...),
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends()
):
    """更新機關單位資料"""
    updated = await agency_service.update_agency(
        db, agency_id=agency_id, agency_update=agency
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到要更新的機關單位"
        )
    return updated


@router.post(
    "/{agency_id}/delete",
    summary="刪除機關"
)
async def delete_agency(
    agency_id: int,
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends()
):
    """刪除機關單位"""
    try:
        success = await agency_service.delete_agency(db, agency_id=agency_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到要刪除的機關單位"
            )
        return {
            "success": True,
            "message": "機關單位已刪除",
            "deleted_id": agency_id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post(
    "/statistics",
    response_model=AgencyStatistics,
    summary="取得機關統計資料"
)
async def get_agency_statistics(
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends()
):
    """取得機關統計資料"""
    return await agency_service.get_agency_statistics(db)


# ============================================================================
# 向後相容：保留 GET 端點（已棄用，將在未來版本移除）
# ============================================================================

@router.get(
    "",
    response_model=AgenciesResponse,
    summary="[相容] 取得機關列表",
    deprecated=True
)
async def list_agencies_legacy(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_stats: bool = True,
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends()
):
    """
    [相容性端點] 取得機關列表

    此端點為向後相容保留，請改用 POST /agencies/list
    """
    if include_stats:
        return await agency_service.get_agencies_with_stats(
            db, skip=skip, limit=limit, search=search
        )
    else:
        agencies = await agency_service.get_agencies(db, skip=skip, limit=limit)
        return AgenciesResponse(agencies=agencies, total=len(agencies), returned=len(agencies))


@router.get(
    "/statistics",
    response_model=AgencyStatistics,
    summary="[相容] 取得統計資料",
    deprecated=True
)
async def get_statistics_legacy(
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends()
):
    """此端點為向後相容保留，請改用 POST /agencies/statistics"""
    return await agency_service.get_agency_statistics(db)
