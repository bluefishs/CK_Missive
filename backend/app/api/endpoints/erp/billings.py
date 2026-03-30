"""ERP 請款 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_service, get_async_db
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


@router.post("/list-with-details")
async def list_billings_with_details(
    req: ERPQuotationIdRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """取得請款列表 — 含關聯發票 + 廠商應付 (期別整合視圖)"""
    from app.extended.models.erp import ERPBilling

    result = await db.execute(
        select(ERPBilling)
        .where(ERPBilling.erp_quotation_id == req.erp_quotation_id)
        .options(
            selectinload(ERPBilling.linked_invoices),
            selectinload(ERPBilling.linked_payables),
        )
        .order_by(ERPBilling.billing_date, ERPBilling.id)
    )
    billings = result.scalars().all()

    data = []
    for b in billings:
        data.append({
            "id": b.id,
            "billing_period": b.billing_period,
            "billing_date": str(b.billing_date) if b.billing_date else None,
            "billing_amount": float(b.billing_amount) if b.billing_amount else 0,
            "payment_status": b.payment_status,
            "payment_date": str(b.payment_date) if b.payment_date else None,
            "payment_amount": float(b.payment_amount) if b.payment_amount else None,
            "notes": b.notes,
            "invoices": [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
                    "amount": float(inv.amount) if inv.amount else 0,
                    "tax_amount": float(inv.tax_amount) if inv.tax_amount else 0,
                    "invoice_type": inv.invoice_type,
                    "status": inv.status,
                }
                for inv in (b.linked_invoices or [])
            ],
            "vendor_payables": [
                {
                    "id": vp.id,
                    "vendor_name": vp.vendor_name,
                    "payable_amount": float(vp.payable_amount) if vp.payable_amount else 0,
                    "payment_status": vp.payment_status,
                    "paid_amount": float(vp.paid_amount) if vp.paid_amount else None,
                    "description": vp.description,
                }
                for vp in (b.linked_payables or [])
            ],
        })

    return {"success": True, "data": data}
