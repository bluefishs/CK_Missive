#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
承攬案件管理API端點 (已修復依賴注入)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct

from app.db.database import get_async_db
from app.extended.models import User, ContractProject
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.services.project_service import ProjectService

router = APIRouter()

@router.get("/years", summary="獲取專案年度選項")
async def get_project_years(db: AsyncSession = Depends(get_async_db)):
    """獲取所有專案的年度選項"""
    try:
        query = select(distinct(ContractProject.year)).where(ContractProject.year.isnot(None)).order_by(ContractProject.year.desc())
        result = await db.execute(query)
        years = [row[0] for row in result.fetchall()]
        return {"years": years}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取年度選項失敗: {str(e)}"
        )

@router.get("/categories", summary="獲取專案類別選項")
async def get_project_categories(db: AsyncSession = Depends(get_async_db)):
    """獲取所有專案的類別選項"""
    try:
        query = select(distinct(ContractProject.category)).where(ContractProject.category.isnot(None)).order_by(ContractProject.category)
        result = await db.execute(query)
        categories = [row[0] for row in result.fetchall()]
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取類別選項失敗: {str(e)}"
        )

@router.get("/statuses", summary="獲取專案狀態選項")
async def get_project_statuses(db: AsyncSession = Depends(get_async_db)):
    """獲取所有專案的狀態選項"""
    try:
        query = select(distinct(ContractProject.status)).where(ContractProject.status.isnot(None)).order_by(ContractProject.status)
        result = await db.execute(query)
        statuses = [row[0] for row in result.fetchall()]
        return {"statuses": statuses}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取狀態選項失敗: {str(e)}"
        )

@router.get("/statistics", summary="獲取專案統計資料")
async def get_project_statistics(db: AsyncSession = Depends(get_async_db), project_service: ProjectService = Depends()):
    """獲取專案統計資料"""
    return await project_service.get_project_statistics(db)

@router.get("/", response_model=ProjectListResponse)
async def get_projects(
    db: AsyncSession = Depends(get_async_db),
    project_service: ProjectService = Depends(),
    skip: int = 0, limit: int = 100, search: Optional[str] = None,
    year: Optional[int] = None, category: Optional[str] = None, status: Optional[str] = None
):
    class QueryParams:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)
    params = QueryParams(skip=skip, limit=limit, search=search, year=year, category=category, status=status)
    result = await project_service.get_projects(db, params)
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in result["projects"]],
        total=result["total"],
        skip=skip,
        limit=limit
    )

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate, db: AsyncSession = Depends(get_async_db), project_service: ProjectService = Depends()):
    try:
        project = await project_service.create_project(db, project_data)
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_async_db), project_service: ProjectService = Depends()):
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="承攬案件不存在")
    return ProjectResponse.model_validate(project)

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, project_data: ProjectUpdate, db: AsyncSession = Depends(get_async_db), project_service: ProjectService = Depends()):
    project = await project_service.update_project(db, project_id, project_data)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="承攬案件不存在")
    return ProjectResponse.model_validate(project)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_async_db), project_service: ProjectService = Depends()):
    success = await project_service.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="承攬案件不存在")
