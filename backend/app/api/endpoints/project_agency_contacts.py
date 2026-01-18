#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
專案機關承辦 API 端點
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_async_db
from app.services.project_agency_contact_service import ProjectAgencyContactService
from app.schemas.project_agency_contact import (
    ProjectAgencyContactCreate,
    ProjectAgencyContactUpdate,
    ProjectAgencyContactResponse,
    ProjectAgencyContactListResponse,
    UpdateContactRequest
)
from app.core.dependencies import require_auth
from app.extended.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

# 服務實例
agency_contact_service = ProjectAgencyContactService()


@router.post("/list", response_model=ProjectAgencyContactListResponse)
async def get_project_agency_contacts(
    project_id: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """取得專案的機關承辦列表"""
    try:
        result = await agency_contact_service.get_contacts_by_project(db, project_id)
        return result
    except Exception as e:
        logger.error(f"取得機關承辦列表失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"取得機關承辦列表失敗: {str(e)}")


@router.post("/detail", response_model=ProjectAgencyContactResponse)
async def get_agency_contact(
    contact_id: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """取得單一機關承辦資料"""
    contact = await agency_contact_service.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="找不到該機關承辦資料")
    return contact


@router.post("/create", response_model=ProjectAgencyContactResponse)
async def create_agency_contact(
    contact: ProjectAgencyContactCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """建立機關承辦資料"""
    try:
        result = await agency_contact_service.create_contact(db, contact)
        return result
    except Exception as e:
        logger.error(f"建立機關承辦失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"建立機關承辦失敗: {str(e)}")


# 注意：UpdateContactRequest 已統一定義於 app/schemas/project_agency_contact.py


@router.post("/update", response_model=ProjectAgencyContactResponse)
async def update_agency_contact(
    request: UpdateContactRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """更新機關承辦資料"""
    try:
        # 從請求中提取更新資料
        contact_update = ProjectAgencyContactUpdate(
            contact_name=request.contact_name,
            position=request.position,
            department=request.department,
            phone=request.phone,
            mobile=request.mobile,
            email=request.email,
            is_primary=request.is_primary,
            notes=request.notes
        )
        result = await agency_contact_service.update_contact(db, request.contact_id, contact_update)
        if not result:
            raise HTTPException(status_code=404, detail="找不到該機關承辦資料")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新機關承辦失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新機關承辦失敗: {str(e)}")


@router.post("/delete")
async def delete_agency_contact(
    contact_id: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """刪除機關承辦資料"""
    try:
        success = await agency_contact_service.delete_contact(db, contact_id)
        if not success:
            raise HTTPException(status_code=404, detail="找不到該機關承辦資料")
        return {"success": True, "message": "刪除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除機關承辦失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"刪除機關承辦失敗: {str(e)}")
