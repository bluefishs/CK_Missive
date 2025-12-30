"""
協力廠商管理API端點 (已修復回應結構)
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import User
from app.api.endpoints.auth import get_current_user
from app.schemas.vendor import Vendor, VendorCreate, VendorUpdate
from app.services.vendor_service import VendorService

router = APIRouter()
vendor_service = VendorService()

@router.post("/", response_model=Vendor, status_code=status.HTTP_201_CREATED)
async def create_vendor(vendor: VendorCreate, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    try:
        return await vendor_service.create_vendor(db, vendor)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/", response_model=Dict[str, Any])
async def get_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """ 獲取廠商列表，並回傳符合前端期望的結構 """
    vendors = await vendor_service.get_vendors(db, skip, limit)
    total = await vendor_service.get_total_vendors(db) # 假設 service 中有這個方法
    return {"vendors": vendors, "total": total}

@router.get("/statistics")
async def get_vendor_statistics(db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    return await vendor_service.get_vendor_statistics(db)

@router.get("/{vendor_id}", response_model=Vendor)
async def get_vendor(vendor_id: int, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    db_vendor = await vendor_service.get_vendor(db, vendor_id)
    if not db_vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的廠商")
    return db_vendor

@router.put("/{vendor_id}", response_model=Vendor)
async def update_vendor(vendor_id: int, vendor: VendorUpdate, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    updated_vendor = await vendor_service.update_vendor(db, vendor_id, vendor)
    if not updated_vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到要更新的廠商")
    return updated_vendor

@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(vendor_id: int, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    try:
        success = await vendor_service.delete_vendor(db, vendor_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到要刪除的廠商")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))