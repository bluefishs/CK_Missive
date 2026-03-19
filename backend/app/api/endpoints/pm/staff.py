"""PM 案件人員 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.services.pm import PMCaseStaffService
from app.schemas.pm import (
    PMCaseStaffCreate, PMCaseStaffUpdate,
    PMIdRequest, PMCaseIdByFieldRequest, PMStaffUpdateRequest,
)
from app.schemas.common import SuccessResponse, DeleteResponse

router = APIRouter()


@router.post("/list")
async def list_staff(
    req: PMCaseIdByFieldRequest,
    service: PMCaseStaffService = Depends(get_service(PMCaseStaffService)),
):
    """取得案件人員"""
    items = await service.get_by_case(req.pm_case_id)
    return SuccessResponse(data=items)


@router.post("/create")
async def create_staff(
    data: PMCaseStaffCreate,
    service: PMCaseStaffService = Depends(get_service(PMCaseStaffService)),
):
    """建立案件人員"""
    result = await service.create(data)
    return SuccessResponse(data=result, message="人員新增成功")


@router.post("/update")
async def update_staff(
    req: PMStaffUpdateRequest,
    service: PMCaseStaffService = Depends(get_service(PMCaseStaffService)),
):
    """更新案件人員"""
    result = await service.update(req.id, req.data)
    if not result:
        raise HTTPException(status_code=404, detail="人員不存在")
    return SuccessResponse(data=result, message="人員更新成功")


@router.post("/delete")
async def delete_staff(
    req: PMIdRequest,
    service: PMCaseStaffService = Depends(get_service(PMCaseStaffService)),
):
    """刪除案件人員"""
    success = await service.delete(req.id)
    if not success:
        raise HTTPException(status_code=404, detail="人員不存在")
    return DeleteResponse(deleted_id=req.id)
