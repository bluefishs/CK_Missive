"""ERP 發票 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.services.erp import ERPInvoiceService
from app.schemas.erp import (
    ERPInvoiceCreate, ERPInvoiceUpdate,
    ERPIdRequest, ERPQuotationIdRequest, ERPInvoiceUpdateRequest,
)
from app.schemas.common import SuccessResponse, DeleteResponse

router = APIRouter()


@router.post("/list")
async def list_invoices(
    req: ERPQuotationIdRequest,
    service: ERPInvoiceService = Depends(get_service(ERPInvoiceService)),
):
    """取得報價單發票"""
    items = await service.get_by_quotation(req.erp_quotation_id)
    return SuccessResponse(data=items)


@router.post("/create")
async def create_invoice(
    data: ERPInvoiceCreate,
    service: ERPInvoiceService = Depends(get_service(ERPInvoiceService)),
):
    """建立發票"""
    result = await service.create(data)
    return SuccessResponse(data=result, message="發票建立成功")


@router.post("/update")
async def update_invoice(
    req: ERPInvoiceUpdateRequest,
    service: ERPInvoiceService = Depends(get_service(ERPInvoiceService)),
):
    """更新發票"""
    result = await service.update(req.id, req.data)
    if not result:
        raise HTTPException(status_code=404, detail="發票不存在")
    return SuccessResponse(data=result, message="發票更新成功")


@router.post("/delete")
async def delete_invoice(
    req: ERPIdRequest,
    service: ERPInvoiceService = Depends(get_service(ERPInvoiceService)),
):
    """刪除發票"""
    success = await service.delete(req.id)
    if not success:
        raise HTTPException(status_code=404, detail="發票不存在")
    return DeleteResponse(deleted_id=req.id)
