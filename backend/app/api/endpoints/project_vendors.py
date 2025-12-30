#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案件與廠商關聯管理API端點
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import ContractProject, PartnerVendor, project_vendor_association
from app.schemas.project_vendor import (
    ProjectVendorCreate, 
    ProjectVendorUpdate, 
    ProjectVendorResponse,
    ProjectVendorListResponse
)

router = APIRouter()

@router.post("/")
async def create_project_vendor_association(
    association_data: ProjectVendorCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """建立案件與廠商關聯"""
    
    # 檢查案件是否存在
    project_query = select(ContractProject).where(
        ContractProject.id == association_data.project_id
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="承攬案件不存在")
    
    # 檢查廠商是否存在
    vendor_query = select(PartnerVendor).where(
        PartnerVendor.id == association_data.vendor_id
    )
    vendor_result = await db.execute(vendor_query)
    vendor = vendor_result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="廠商不存在")
    
    # 檢查是否已存在關聯
    existing_query = select(project_vendor_association).where(
        (project_vendor_association.c.project_id == association_data.project_id) &
        (project_vendor_association.c.vendor_id == association_data.vendor_id)
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.fetchone()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="該廠商已與此案件建立關聯"
        )
    
    # 建立關聯
    insert_stmt = insert(project_vendor_association).values(
        project_id=association_data.project_id,
        vendor_id=association_data.vendor_id,
        role=association_data.role,
        contract_amount=association_data.contract_amount,
        start_date=association_data.start_date,
        end_date=association_data.end_date,
        status=association_data.status or 'active'
    )
    
    await db.execute(insert_stmt)
    await db.commit()
    
    return {
        "message": "案件與廠商關聯建立成功",
        "project_id": association_data.project_id,
        "vendor_id": association_data.vendor_id
    }

@router.get("/project/{project_id}", response_model=ProjectVendorListResponse)
async def get_project_vendor_associations(
    project_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """取得特定案件的所有廠商關聯"""
    
    # 檢查案件是否存在
    project_query = select(ContractProject).where(ContractProject.id == project_id)
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="承攬案件不存在")
    
    # 查詢關聯資料
    query = select(
        project_vendor_association.c.project_id,
        project_vendor_association.c.vendor_id,
        project_vendor_association.c.role,
        project_vendor_association.c.contract_amount,
        project_vendor_association.c.start_date,
        project_vendor_association.c.end_date,
        project_vendor_association.c.status,
        project_vendor_association.c.created_at,
        project_vendor_association.c.updated_at,
        PartnerVendor.vendor_name,
        PartnerVendor.vendor_code,
        PartnerVendor.contact_person,
        PartnerVendor.phone,
        PartnerVendor.business_type
    ).select_from(
        project_vendor_association.join(
            PartnerVendor,
            project_vendor_association.c.vendor_id == PartnerVendor.id
        )
    ).where(project_vendor_association.c.project_id == project_id)
    
    result = await db.execute(query)
    associations_data = result.fetchall()
    
    associations = []
    for row in associations_data:
        associations.append(ProjectVendorResponse(
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
            updated_at=row.updated_at
        ))
    
    return ProjectVendorListResponse(
        project_id=project_id,
        project_name=project.project_name,
        associations=associations,
        total=len(associations)
    )

@router.get("/vendor/{vendor_id}")
async def get_vendor_project_associations(
    vendor_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """取得特定廠商的所有案件關聯"""
    
    # 檢查廠商是否存在
    vendor_query = select(PartnerVendor).where(PartnerVendor.id == vendor_id)
    vendor_result = await db.execute(vendor_query)
    vendor = vendor_result.scalar_one_or_none()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="廠商不存在")
    
    # 查詢關聯資料
    query = select(
        project_vendor_association.c.project_id,
        project_vendor_association.c.vendor_id,
        project_vendor_association.c.role,
        project_vendor_association.c.contract_amount,
        project_vendor_association.c.start_date,
        project_vendor_association.c.end_date,
        project_vendor_association.c.status,
        project_vendor_association.c.created_at,
        project_vendor_association.c.updated_at,
        ContractProject.project_name,
        ContractProject.project_code,
        ContractProject.year,
        ContractProject.category,
        ContractProject.status.label('project_status')
    ).select_from(
        project_vendor_association.join(
            ContractProject,
            project_vendor_association.c.project_id == ContractProject.id
        )
    ).where(project_vendor_association.c.vendor_id == vendor_id)
    
    result = await db.execute(query)
    associations_data = result.fetchall()
    
    associations = []
    for row in associations_data:
        associations.append({
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
            "updated_at": row.updated_at
        })
    
    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.vendor_name,
        "associations": associations,
        "total": len(associations)
    }

@router.put("/project/{project_id}/vendor/{vendor_id}")
async def update_project_vendor_association(
    project_id: int,
    vendor_id: int,
    association_data: ProjectVendorUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """更新案件與廠商關聯資訊"""
    
    # 檢查關聯是否存在
    check_query = select(project_vendor_association).where(
        (project_vendor_association.c.project_id == project_id) &
        (project_vendor_association.c.vendor_id == vendor_id)
    )
    check_result = await db.execute(check_query)
    existing = check_result.fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="案件與廠商關聯不存在")
    
    # 更新關聯資料
    update_data = association_data.dict(exclude_unset=True)
    if update_data:
        update_stmt = update(project_vendor_association).where(
            (project_vendor_association.c.project_id == project_id) &
            (project_vendor_association.c.vendor_id == vendor_id)
        ).values(**update_data)
        
        await db.execute(update_stmt)
        await db.commit()
    
    return {
        "message": "案件與廠商關聯更新成功",
        "project_id": project_id,
        "vendor_id": vendor_id
    }

@router.delete("/project/{project_id}/vendor/{vendor_id}")
async def delete_project_vendor_association(
    project_id: int,
    vendor_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """刪除案件與廠商關聯"""
    
    # 檢查關聯是否存在
    check_query = select(project_vendor_association).where(
        (project_vendor_association.c.project_id == project_id) &
        (project_vendor_association.c.vendor_id == vendor_id)
    )
    check_result = await db.execute(check_query)
    existing = check_result.fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="案件與廠商關聯不存在")
    
    # 刪除關聯
    delete_stmt = delete(project_vendor_association).where(
        (project_vendor_association.c.project_id == project_id) &
        (project_vendor_association.c.vendor_id == vendor_id)
    )
    
    await db.execute(delete_stmt)
    await db.commit()
    
    return {
        "message": "案件與廠商關聯已成功刪除",
        "project_id": project_id,
        "vendor_id": vendor_id
    }

@router.get("/")
async def get_all_associations(
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(100, ge=1, le=1000, description="限制筆數"),
    project_id: Optional[int] = Query(None, description="案件ID篩選"),
    vendor_id: Optional[int] = Query(None, description="廠商ID篩選"),
    status: Optional[str] = Query(None, description="狀態篩選"),
    db: AsyncSession = Depends(get_async_db)
):
    """取得所有案件與廠商關聯列表"""
    
    query = select(
        project_vendor_association.c.project_id,
        project_vendor_association.c.vendor_id,
        project_vendor_association.c.role,
        project_vendor_association.c.contract_amount,
        project_vendor_association.c.start_date,
        project_vendor_association.c.end_date,
        project_vendor_association.c.status,
        project_vendor_association.c.created_at,
        project_vendor_association.c.updated_at,
        ContractProject.project_name,
        ContractProject.project_code,
        PartnerVendor.vendor_name,
        PartnerVendor.vendor_code
    ).select_from(
        project_vendor_association.join(
            ContractProject,
            project_vendor_association.c.project_id == ContractProject.id
        ).join(
            PartnerVendor,
            project_vendor_association.c.vendor_id == PartnerVendor.id
        )
    )
    
    # 篩選條件
    if project_id:
        query = query.where(project_vendor_association.c.project_id == project_id)
    
    if vendor_id:
        query = query.where(project_vendor_association.c.vendor_id == vendor_id)
    
    if status:
        query = query.where(project_vendor_association.c.status == status)
    
    # 分頁
    query = query.order_by(project_vendor_association.c.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    associations_data = result.fetchall()
    
    associations = []
    for row in associations_data:
        associations.append({
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
            "updated_at": row.updated_at
        })
    
    return {
        "associations": associations,
        "total": len(associations),
        "skip": skip,
        "limit": limit
    }