"""
機關單位管理 API 端點 (已修復依賴注入)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.api.endpoints.auth import get_current_user
from app.extended.models import User
from app.schemas.agency import Agency, AgencyCreate, AgencyUpdate, AgenciesResponse, AgencyStatistics
from app.services.agency_service import AgencyService

router = APIRouter()

# **關鍵修復：移除在頂層建立的實例，改為使用 Depends 注入**
# agency_service = AgencyService()

@router.post("/", response_model=Agency, status_code=status.HTTP_201_CREATED)
async def create_agency(
    agency: AgencyCreate,
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends(),
    current_user: User = Depends(get_current_user)
):
    try:
        return await agency_service.create_agency(db=db, agency=agency)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/", response_model=AgenciesResponse)
async def get_agencies(
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends(),
    skip: int = 0, limit: int = 100, search: Optional[str] = None, include_stats: bool = True
):
    if include_stats:
        return await agency_service.get_agencies_with_stats(db, skip=skip, limit=limit, search=search)
    else:
        agencies = await agency_service.get_agencies(db, skip=skip, limit=limit)
        return AgenciesResponse(agencies=agencies, total=len(agencies), returned=len(agencies))

@router.get("/statistics", response_model=AgencyStatistics)
async def get_agency_statistics(
    db: AsyncSession = Depends(get_async_db),
    agency_service: AgencyService = Depends(),
    current_user: User = Depends(get_current_user)
):
    return await agency_service.get_agency_statistics(db)

@router.get("/{agency_id}", response_model=Agency)
async def get_agency(
    agency_id: int, db: AsyncSession = Depends(get_async_db), agency_service: AgencyService = Depends(), current_user: User = Depends(get_current_user)
):
    db_agency = await agency_service.get_agency(db, agency_id=agency_id)
    if db_agency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的機關單位")
    return db_agency

@router.put("/{agency_id}", response_model=Agency)
async def update_agency(
    agency_id: int, agency: AgencyUpdate, db: AsyncSession = Depends(get_async_db), agency_service: AgencyService = Depends(), current_user: User = Depends(get_current_user)
):
    updated_agency = await agency_service.update_agency(db, agency_id=agency_id, agency_update=agency)
    if updated_agency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到要更新的機關單位")
    return updated_agency

@router.delete("/{agency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agency(
    agency_id: int, db: AsyncSession = Depends(get_async_db), agency_service: AgencyService = Depends(), current_user: User = Depends(get_current_user)
):
    try:
        success = await agency_service.delete_agency(db, agency_id=agency_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到要刪除的機關單位")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
