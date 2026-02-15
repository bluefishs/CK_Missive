#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
承攬案件統計與選項 API 端點

包含：年度選項、類別選項、狀態選項、統計資料

@version 4.0.0
@date 2026-02-11

變更紀錄:
- v4.0.0: 模組化拆分，從 projects.py 提取統計端點
- v3.0.0: ProjectService 升級為工廠模式
- v2.0.0: 新增認證依賴
"""
from fastapi import APIRouter, Depends

from app.schemas.common import SuccessResponse
from app.services.project_service import ProjectService
from app.core.dependencies import (
    get_service,
    require_auth,
)
from app.extended.models import User

router = APIRouter()


# ============================================================================
# 選項 API（下拉選單用）
# ============================================================================

@router.post("/years", summary="獲取專案年度選項")
async def get_project_years(
    project_service: ProjectService = Depends(get_service(ProjectService)),
    current_user: User = Depends(require_auth())
) -> SuccessResponse:
    """獲取所有專案的年度選項（需要登入）"""
    years = await project_service.get_year_options()
    return SuccessResponse(
        success=True,
        data={"years": years}
    )


@router.post("/categories", summary="獲取專案類別選項")
async def get_project_categories(
    project_service: ProjectService = Depends(get_service(ProjectService)),
    current_user: User = Depends(require_auth())
) -> SuccessResponse:
    """獲取所有專案的類別選項（需要登入）"""
    categories = await project_service.get_category_options()
    return SuccessResponse(
        success=True,
        data={"categories": categories}
    )


@router.post("/statuses", summary="獲取專案狀態選項")
async def get_project_statuses(
    project_service: ProjectService = Depends(get_service(ProjectService)),
    current_user: User = Depends(require_auth())
) -> SuccessResponse:
    """獲取所有專案的狀態選項（需要登入）"""
    statuses = await project_service.get_status_options()
    return SuccessResponse(
        success=True,
        data={"statuses": statuses}
    )


# ============================================================================
# 統計 API
# ============================================================================

@router.post("/statistics", summary="獲取專案統計資料")
async def get_project_statistics(
    project_service: ProjectService = Depends(get_service(ProjectService)),
    current_user: User = Depends(require_auth())
) -> SuccessResponse:
    """獲取專案統計資料（需要登入）"""
    stats = await project_service.get_project_statistics()
    return SuccessResponse(
        success=True,
        data=stats
    )
