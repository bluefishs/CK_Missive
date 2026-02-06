#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件與廠商關聯管理API端點 (POST-only 資安機制)
所有端點需要認證。

v2.0.0 - 遷移至 ProjectVendorRepository 資料存取層
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.core.dependencies import require_auth
from app.extended.models import User
from app.repositories.project_vendor_repository import ProjectVendorRepository
from app.schemas.project_vendor import (
    ProjectVendorCreate,
    ProjectVendorUpdate,
    ProjectVendorResponse,
    ProjectVendorListResponse,
    VendorAssociationListQuery,
)

router = APIRouter()


def _get_repo(db: AsyncSession) -> ProjectVendorRepository:
    return ProjectVendorRepository(db)


# ========== POST-only API 端點 ==========

@router.post("", summary="建立案件與廠商關聯")
async def create_project_vendor_association(
    association_data: ProjectVendorCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """建立案件與廠商關聯"""
    repo = _get_repo(db)

    # 檢查案件是否存在
    if not await repo.project_exists(association_data.project_id):
        raise HTTPException(status_code=404, detail="承攬案件不存在")

    # 檢查廠商是否存在
    if not await repo.vendor_exists(association_data.vendor_id):
        raise HTTPException(status_code=404, detail="廠商不存在")

    # 檢查是否已存在關聯
    if await repo.exists(association_data.project_id, association_data.vendor_id):
        raise HTTPException(status_code=400, detail="該廠商已與此案件建立關聯")

    # 建立關聯
    await repo.create_association({
        "project_id": association_data.project_id,
        "vendor_id": association_data.vendor_id,
        "role": association_data.role,
        "contract_amount": association_data.contract_amount,
        "start_date": association_data.start_date,
        "end_date": association_data.end_date,
        "status": association_data.status or "active",
    })

    return {
        "message": "案件與廠商關聯建立成功",
        "project_id": association_data.project_id,
        "vendor_id": association_data.vendor_id,
    }


@router.post(
    "/project/{project_id}/list",
    response_model=ProjectVendorListResponse,
    summary="取得案件廠商列表",
)
async def get_project_vendor_associations(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """取得特定案件的所有廠商關聯"""
    repo = _get_repo(db)

    # 檢查案件是否存在
    project = await repo.project_exists(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="承攬案件不存在")

    # 查詢關聯資料
    rows = await repo.get_project_associations(project_id)

    associations = [
        ProjectVendorResponse(
            project_id=row.project_id,
            vendor_id=row.vendor_id,
            vendor_name=row.vendor_name,
            vendor_code=row.vendor_code,
            vendor_contact_person=row.contact_person,
            vendor_phone=row.phone,
            vendor_business_type=row.business_type,
            role=row.role,
            contract_amount=row.contract_amount,
            start_date=row.start_date,
            end_date=row.end_date,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]

    return ProjectVendorListResponse(
        project_id=project_id,
        project_name=project.project_name,
        associations=associations,
        total=len(associations),
    )


@router.post("/vendor/{vendor_id}/projects", summary="取得廠商參與案件列表")
async def get_vendor_project_associations(
    vendor_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """取得特定廠商的所有案件關聯"""
    repo = _get_repo(db)

    # 檢查廠商是否存在
    vendor = await repo.vendor_exists(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="廠商不存在")

    # 查詢關聯資料
    rows = await repo.get_vendor_associations(vendor_id)

    associations = [
        {
            "project_id": row.project_id,
            "project_name": row.project_name,
            "project_code": row.project_code,
            "project_year": row.year,
            "project_category": row.category,
            "project_status": row.project_status,
            "vendor_id": row.vendor_id,
            "role": row.role,
            "contract_amount": row.contract_amount,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "association_status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.vendor_name,
        "associations": associations,
        "total": len(associations),
    }


@router.post(
    "/project/{project_id}/vendor/{vendor_id}/update",
    summary="更新案件與廠商關聯",
)
async def update_project_vendor_association(
    project_id: int,
    vendor_id: int,
    association_data: ProjectVendorUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """更新案件與廠商關聯資訊"""
    repo = _get_repo(db)

    # 檢查關聯是否存在
    if not await repo.exists(project_id, vendor_id):
        raise HTTPException(status_code=404, detail="案件與廠商關聯不存在")

    # 更新關聯資料
    update_data = association_data.model_dump(exclude_unset=True)
    if update_data:
        await repo.update_association(project_id, vendor_id, update_data)

    return {
        "message": "案件與廠商關聯更新成功",
        "project_id": project_id,
        "vendor_id": vendor_id,
    }


@router.post(
    "/project/{project_id}/vendor/{vendor_id}/delete",
    summary="刪除案件與廠商關聯",
)
async def delete_project_vendor_association(
    project_id: int,
    vendor_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """刪除案件與廠商關聯"""
    repo = _get_repo(db)

    # 檢查關聯是否存在
    if not await repo.exists(project_id, vendor_id):
        raise HTTPException(status_code=404, detail="案件與廠商關聯不存在")

    # 刪除關聯
    await repo.delete_association(project_id, vendor_id)

    return {
        "message": "案件與廠商關聯已成功刪除",
        "project_id": project_id,
        "vendor_id": vendor_id,
    }


@router.post("/list", summary="取得所有廠商關聯列表")
async def get_all_associations(
    query: VendorAssociationListQuery = Body(default=VendorAssociationListQuery()),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """取得所有案件與廠商關聯列表"""
    repo = _get_repo(db)

    rows = await repo.list_all(
        project_id=query.project_id,
        vendor_id=query.vendor_id,
        status=query.status,
        skip=query.skip,
        limit=query.limit,
    )

    associations = [
        {
            "project_id": row.project_id,
            "project_name": row.project_name,
            "project_code": row.project_code,
            "vendor_id": row.vendor_id,
            "vendor_name": row.vendor_name,
            "vendor_code": row.vendor_code,
            "role": row.role,
            "contract_amount": row.contract_amount,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]

    return {
        "associations": associations,
        "total": len(associations),
        "skip": query.skip,
        "limit": query.limit,
    }
