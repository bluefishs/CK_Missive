"""ERP 廠商應付 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.services.erp import ERPVendorPayableService
from app.schemas.erp import (
    ERPVendorPayableCreate, ERPVendorPayableUpdate,
    ERPIdRequest, ERPQuotationIdRequest, ERPPayableUpdateRequest,
)
from app.schemas.common import SuccessResponse, DeleteResponse

router = APIRouter()


@router.post("/list")
async def list_vendor_payables(
    req: ERPQuotationIdRequest,
    service: ERPVendorPayableService = Depends(get_service(ERPVendorPayableService)),
):
    """取得報價單廠商應付"""
    items = await service.get_by_quotation(req.erp_quotation_id)
    return SuccessResponse(data=items)


@router.post("/create")
async def create_vendor_payable(
    data: ERPVendorPayableCreate,
    service: ERPVendorPayableService = Depends(get_service(ERPVendorPayableService)),
):
    """建立廠商應付"""
    result = await service.create(data)
    return SuccessResponse(data=result, message="廠商應付建立成功")


@router.post("/update")
async def update_vendor_payable(
    req: ERPPayableUpdateRequest,
    service: ERPVendorPayableService = Depends(get_service(ERPVendorPayableService)),
):
    """更新廠商應付"""
    result = await service.update(req.id, req.data)
    if not result:
        raise HTTPException(status_code=404, detail="廠商應付不存在")
    return SuccessResponse(data=result, message="廠商應付更新成功")


@router.post("/delete")
async def delete_vendor_payable(
    req: ERPIdRequest,
    service: ERPVendorPayableService = Depends(get_service(ERPVendorPayableService)),
):
    """刪除廠商應付"""
    success = await service.delete(req.id)
    if not success:
        raise HTTPException(status_code=404, detail="廠商應付不存在")
    return DeleteResponse(deleted_id=req.id)
