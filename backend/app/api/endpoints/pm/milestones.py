"""PM 里程碑 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.services.pm import PMMilestoneService
from app.schemas.pm import (
    PMMilestoneCreate, PMMilestoneUpdate,
    PMIdRequest, PMCaseIdByFieldRequest, PMMilestoneUpdateRequest,
)
from app.schemas.common import SuccessResponse, DeleteResponse

router = APIRouter()


@router.post("/list")
async def list_milestones(
    req: PMCaseIdByFieldRequest,
    service: PMMilestoneService = Depends(get_service(PMMilestoneService)),
):
    """取得案件里程碑"""
    items = await service.get_by_case(req.pm_case_id)
    return SuccessResponse(data=items)


@router.post("/create")
async def create_milestone(
    data: PMMilestoneCreate,
    service: PMMilestoneService = Depends(get_service(PMMilestoneService)),
):
    """建立里程碑"""
    result = await service.create(data)
    return SuccessResponse(data=result, message="里程碑建立成功")


@router.post("/update")
async def update_milestone(
    req: PMMilestoneUpdateRequest,
    service: PMMilestoneService = Depends(get_service(PMMilestoneService)),
):
    """更新里程碑"""
    result = await service.update(req.id, req.data)
    if not result:
        raise HTTPException(status_code=404, detail="里程碑不存在")
    return SuccessResponse(data=result, message="里程碑更新成功")


@router.post("/delete")
async def delete_milestone(
    req: PMIdRequest,
    service: PMMilestoneService = Depends(get_service(PMMilestoneService)),
):
    """刪除里程碑"""
    success = await service.delete(req.id)
    if not success:
        raise HTTPException(status_code=404, detail="里程碑不存在")
    return DeleteResponse(deleted_id=req.id)
