#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
承攬案件管理 API 端點

v2.0 - 2026-01-10
- 新增認證依賴：所有端點需要登入
- 新增行級別權限過濾：非管理員只能查看關聯專案
- 新增權限檢查：建立/編輯/刪除需要對應權限
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
    ProjectListQuery,
)
from app.schemas.common import (
    PaginationMeta,
    DeleteResponse,
    SuccessResponse,
    SortOrder,
)
from app.services.project_service import ProjectService
from app.core.dependencies import (
    get_project_service,
    require_auth,
    require_permission,
)
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ForbiddenException,
)
from app.extended.models import User

router = APIRouter()

# 注意：ProjectListQuery 已統一定義於 app/schemas/project.py


# ============================================================================
# 專案列表 API
# ============================================================================

@router.post(
    "/list",
    response_model=ProjectListResponse,
    summary="查詢專案列表",
    description="使用統一分頁格式查詢專案列表（含行級別權限過濾）"
)
async def list_projects(
    query: ProjectListQuery = Body(default=ProjectListQuery()),
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_auth())
):
    """
    查詢專案列表（POST-only 資安機制）

    🔒 權限規則：
    - 需要登入認證
    - superuser/admin: 可查看所有專案
    - 一般使用者: 只能查看自己關聯的專案

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

    # 傳遞 current_user 進行行級別權限過濾
    result = await project_service.get_projects(db, params, current_user)

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
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_auth())
) -> SuccessResponse:
    """獲取所有專案的年度選項（需要登入）"""
    years = await project_service.get_year_options(db)
    return SuccessResponse(
        success=True,
        data={"years": years}
    )


@router.post("/categories", summary="獲取專案類別選項")
async def get_project_categories(
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_auth())
) -> SuccessResponse:
    """獲取所有專案的類別選項（需要登入）"""
    categories = await project_service.get_category_options(db)
    return SuccessResponse(
        success=True,
        data={"categories": categories}
    )


@router.post("/statuses", summary="獲取專案狀態選項")
async def get_project_statuses(
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_auth())
) -> SuccessResponse:
    """獲取所有專案的狀態選項（需要登入）"""
    statuses = await project_service.get_status_options(db)
    return SuccessResponse(
        success=True,
        data={"statuses": statuses}
    )


@router.post("/statistics", summary="獲取專案統計資料")
async def get_project_statistics(
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_auth())
) -> SuccessResponse:
    """獲取專案統計資料（需要登入）"""
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
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_permission("projects:create"))
):
    """
    建立新專案

    🔒 權限要求：projects:create

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
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_auth())
):
    """
    取得單一專案詳情

    🔒 權限規則：
    - 需要登入認證
    - 管理員可查看所有專案
    - 一般使用者只能查看自己關聯的專案
    """
    project = await project_service.get_project(db, project_id)
    if not project:
        raise NotFoundException(resource="承攬案件", resource_id=project_id)

    # 檢查非管理員是否有權限查看此專案
    if not current_user.is_admin and not current_user.is_superuser:
        # 檢查使用者是否與此專案有關聯
        has_access = await project_service.check_user_project_access(
            db, current_user.id, project_id
        )
        if not has_access:
            raise ForbiddenException("您沒有權限查看此專案")

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
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_permission("projects:edit"))
):
    """
    更新專案資料

    🔒 權限要求：projects:edit

    注意：一般使用者只能更新自己關聯的專案
    """
    # 檢查非管理員是否有權限編輯此專案
    if not current_user.is_admin and not current_user.is_superuser:
        has_access = await project_service.check_user_project_access(
            db, current_user.id, project_id
        )
        if not has_access:
            raise ForbiddenException("您沒有權限編輯此專案")

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
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(require_permission("projects:delete"))
):
    """
    刪除專案

    🔒 權限要求：projects:delete（通常只有管理員）

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
