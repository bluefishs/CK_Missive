#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
承攬案件管理 API 端點

使用統一回應格式和錯誤處理機制
"""
from typing import Optional
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.database import get_async_db
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from app.schemas.common import (
    PaginationMeta,
    DeleteResponse,
    SuccessResponse,
    SortOrder,
)
from app.services.project_service import ProjectService
from app.core.dependencies import get_project_service
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
)

router = APIRouter()


# ============================================================================
# 查詢參數 Schema
# ============================================================================

class ProjectListQuery(BaseModel):
    """專案列表查詢參數（統一格式）"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    year: Optional[int] = Field(None, description="年度篩選")
    category: Optional[str] = Field(None, description="類別篩選")
    status: Optional[str] = Field(None, description="狀態篩選")
    sort_by: str = Field(default="id", description="排序欄位")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="排序方向")


# ============================================================================
# 專案列表 API
# ============================================================================

@router.post(
    "/list",
    response_model=ProjectListResponse,
    summary="查詢專案列表",
    description="使用統一分頁格式查詢專案列表"
)
async def list_projects(
    query: ProjectListQuery = Body(default=ProjectListQuery()),
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    查詢專案列表（POST-only 資安機制）

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
    # 計算 skip 值
    skip = (query.page - 1) * query.limit

    # 建立查詢參數物件
    class QueryParams:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    params = QueryParams(
        skip=skip,
        limit=query.limit,
        search=query.search,
        year=query.year,
        category=query.category,
        status=query.status,
        sort_by=query.sort_by,
        sort_order=query.sort_order.value
    )

    result = await project_service.get_projects(db, params)

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in result["projects"]],
        pagination=PaginationMeta.create(
            total=result["total"],
            page=query.page,
            limit=query.limit
        )
    )


# ============================================================================
# 選項 API（下拉選單用）
# ============================================================================

@router.post("/years", summary="獲取專案年度選項")
async def get_project_years(
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
) -> SuccessResponse:
    """獲取所有專案的年度選項"""
    years = await project_service.get_year_options(db)
    return SuccessResponse(
        success=True,
        data={"years": years}
    )


@router.post("/categories", summary="獲取專案類別選項")
async def get_project_categories(
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
) -> SuccessResponse:
    """獲取所有專案的類別選項"""
    categories = await project_service.get_category_options(db)
    return SuccessResponse(
        success=True,
        data={"categories": categories}
    )


@router.post("/statuses", summary="獲取專案狀態選項")
async def get_project_statuses(
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
) -> SuccessResponse:
    """獲取所有專案的狀態選項"""
    statuses = await project_service.get_status_options(db)
    return SuccessResponse(
        success=True,
        data={"statuses": statuses}
    )


@router.post("/statistics", summary="獲取專案統計資料")
async def get_project_statistics(
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
) -> SuccessResponse:
    """獲取專案統計資料"""
    stats = await project_service.get_project_statistics(db)
    return SuccessResponse(
        success=True,
        data=stats
    )


# ============================================================================
# CRUD API
# ============================================================================

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立新專案"
)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    建立新專案

    若專案編號已存在會回傳 409 Conflict 錯誤。
    """
    try:
        project = await project_service.create_project(db, project_data)
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        raise ConflictException(
            message=str(e),
            field="project_code",
            value=project_data.project_code
        )


@router.post(
    "/{project_id}/detail",
    response_model=ProjectResponse,
    summary="取得專案詳情"
)
async def get_project_detail(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
):
    """取得單一專案詳情"""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise NotFoundException(resource="承攬案件", resource_id=project_id)
    return ProjectResponse.model_validate(project)


@router.post(
    "/{project_id}/update",
    response_model=ProjectResponse,
    summary="更新專案"
)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
):
    """更新專案資料"""
    project = await project_service.update_project(db, project_id, project_data)
    if not project:
        raise NotFoundException(resource="承攬案件", resource_id=project_id)
    return ProjectResponse.model_validate(project)


@router.post(
    "/{project_id}/delete",
    response_model=DeleteResponse,
    summary="刪除專案"
)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    刪除專案

    會同時刪除關聯的承辦同仁和廠商資料。
    """
    try:
        success = await project_service.delete_project(db, project_id)
        if not success:
            raise NotFoundException(resource="承攬案件", resource_id=project_id)
        return DeleteResponse(
            success=True,
            message="專案已刪除",
            deleted_id=project_id
        )
    except ValueError as e:
        raise ConflictException(message=str(e))
