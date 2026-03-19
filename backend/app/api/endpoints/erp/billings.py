"""ERP 請款 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.services.erp import ERPBillingService
from app.schemas.erp import (
    ERPBillingCreate, ERPBillingUpdate,
    ERPIdRequest, ERPQuotationIdRequest, ERPBillingUpdateRequest,
)
from app.schemas.common import SuccessResponse, DeleteResponse

router = APIRouter()


@router.post("/list")
async def list_billings(
    req: ERPQuotationIdRequest,
    service: ERPBillingService = Depends(get_service(ERPBillingService)),
):
    """取得報價單請款"""
    items = await service.get_by_quotation(req.erp_quotation_id)
    return SuccessResponse(data=items)


@router.post("/create")
async def create_billing(
    data: ERPBillingCreate,
    service: ERPBillingService = Depends(get_service(ERPBillingService)),
):
    """建立請款"""
    result = await service.create(data)
    return SuccessResponse(data=result, message="請款建立成功")


@router.post("/update")
async def update_billing(
    req: ERPBillingUpdateRequest,
    service: ERPBillingService = Depends(get_service(ERPBillingService)),
):
    """更新請款"""
    result = await service.update(req.id, req.data)
    if not result:
        raise HTTPException(status_code=404, detail="請款不存在")
    return SuccessResponse(data=result, message="請款更新成功")


@router.post("/delete")
async def delete_billing(
    req: ERPIdRequest,
    service: ERPBillingService = Depends(get_service(ERPBillingService)),
):
    """刪除請款"""
    success = await service.delete(req.id)
    if not success:
        raise HTTPException(status_code=404, detail="請款不存在")
    return DeleteResponse(deleted_id=req.id)
