#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件與承辦同仁關聯管理 API 端點 (POST-only 資安機制)

所有端點需要認證。業務邏輯委託 ProjectStaffService 處理。

@version 3.0.0 - 遷移至 Service/Repository 模式
@date 2026-02-28
"""

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_service
from app.extended.models import User
from app.services.project_staff_service import ProjectStaffService
from app.schemas.common import DeleteResponse
from app.schemas.project_staff import (
    ProjectStaffCreate,
    ProjectStaffUpdate,
    ProjectStaffListResponse,
    StaffListQuery,
)

router = APIRouter()


@router.post("", summary="建立案件與承辦同仁關聯")
async def create_project_staff_assignment(
    assignment_data: ProjectStaffCreate,
    service: ProjectStaffService = Depends(get_service(ProjectStaffService)),
    current_user: User = Depends(require_auth()),
):
    """建立案件與承辦同仁關聯"""
    return await service.create_assignment(assignment_data)


@router.post(
    "/project/{project_id}/list",
    response_model=ProjectStaffListResponse,
    summary="取得案件承辦同仁列表",
)
async def get_project_staff_assignments(
    project_id: int,
    service: ProjectStaffService = Depends(get_service(ProjectStaffService)),
    current_user: User = Depends(require_auth()),
):
    """取得特定案件的所有承辦同仁"""
    return await service.get_project_staff(project_id)


@router.post(
    "/project/{project_id}/user/{user_id}/update",
    summary="更新案件與承辦同仁關聯",
)
async def update_project_staff_assignment(
    project_id: int,
    user_id: int,
    assignment_data: ProjectStaffUpdate,
    service: ProjectStaffService = Depends(get_service(ProjectStaffService)),
    current_user: User = Depends(require_auth()),
):
    """更新案件與承辦同仁關聯資訊"""
    return await service.update_assignment(project_id, user_id, assignment_data)


@router.post(
    "/project/{project_id}/user/{user_id}/delete",
    response_model=DeleteResponse,
    summary="刪除案件與承辦同仁關聯",
)
async def delete_project_staff_assignment(
    project_id: int,
    user_id: int,
    service: ProjectStaffService = Depends(get_service(ProjectStaffService)),
    current_user: User = Depends(require_auth()),
):
    """刪除案件與承辦同仁關聯"""
    return await service.delete_assignment(project_id, user_id)


@router.post("/list", summary="取得所有承辦同仁關聯列表")
async def get_all_staff_assignments(
    query: StaffListQuery = Body(default=StaffListQuery()),
    service: ProjectStaffService = Depends(get_service(ProjectStaffService)),
    current_user: User = Depends(require_auth()),
):
    """取得所有案件與承辦同仁關聯列表"""
    return await service.get_all_assignments(query)
