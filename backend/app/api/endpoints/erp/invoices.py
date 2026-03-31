"""ERP 發票 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.services.erp import ERPInvoiceService
from app.schemas.erp import (
    ERPInvoiceCreate, ERPInvoiceUpdate,
    ERPIdRequest, ERPQuotationIdRequest, ERPInvoiceUpdateRequest,
    InvoiceSummaryRequest, CreateFromBillingRequest,
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


@router.post("/summary")
async def get_invoice_summary(
    params: InvoiceSummaryRequest,
    service: ERPInvoiceService = Depends(get_service(ERPInvoiceService)),
):
    """跨案件發票彙總"""
    result = await service.get_invoice_summary(
        invoice_type=params.invoice_type,
        year=params.year,
        skip=params.skip,
        limit=params.limit,
    )
    return SuccessResponse(data=result)


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


@router.post("/create-from-billing")
async def create_invoice_from_billing(
    params: CreateFromBillingRequest,
    service: ERPInvoiceService = Depends(get_service(ERPInvoiceService)),
):
    """從請款記錄開立銷項發票"""
    try:
        invoice = await service.create_from_billing(
            billing_id=params.billing_id,
            invoice_number=params.invoice_number,
            invoice_date=params.invoice_date,
            notes=params.notes,
        )
        return SuccessResponse(data=invoice, message="發票開立成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
