"""ERP 發票 API 端點 (POST-only)"""
from app.schemas.erp.invoice import LinkInvoiceToBillingRequest
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.core.capabilities import require_page_permission
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
    # ⭐ 2026-09-08：本 router 在 `erp/__init__.py` 掛的是**聯集**
    # （`/erp/invoices/summary-view` ∪ `/erp/quotations`），為的是讓報價單詳情的
    # 「帳款紀錄」分頁能讀該張報價單的發票。但**這一支是跨案件、全公司的彙總**，
    # 它就是 `/erp/invoices/summary-view` 那一頁本身 ⇒ 這裡再加一道嚴格的。
    # 依賴會疊加（兩道都要過），所以在聯集之上補嚴格＝這一支維持原本的門檻。
    #
    # ⚠️ 其餘 `/list`／`/create`／`/update`／`/delete`／`/create-from-billing`／
    # `/link-to-billing` 六支**刻意留在聯集**：實查前端，它們全部只被
    # `hooks/business/useERPQuotations.ts` 使用（＝報價單域），
    # 且同一個分頁上的請款（billings）與應付（vendor-payables）本來就掛在
    # `/erp/quotations` ⇒ 同一張報價單的發票與它們是同一個敏感度層級。
    _: object = Depends(require_page_permission("/erp/invoices/summary-view")),
    service: ERPInvoiceService = Depends(get_service(ERPInvoiceService)),
):
    """跨案件發票彙總"""
    result = await service.get_invoice_summary(
        invoice_type=params.invoice_type,
        year=params.year,
        search=params.search,
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
            tax_mode=("exempt" if params.tax_exempt else "taxable"),
            invoice_kind=params.invoice_kind,
            buyer_name=params.buyer_name,
            buyer_tax_id=params.buyer_tax_id,
            invoice_remark=params.invoice_remark,
        )
        return SuccessResponse(data=invoice, message="發票開立成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/link-to-billing")
async def link_invoice_to_billing(
    params: LinkInvoiceToBillingRequest,
    service: ERPInvoiceService = Depends(get_service(ERPInvoiceService)),
):
    """把已登錄但未關聯的發票掛到請款（2026-09-04；規則見 service.link_to_billing）"""
    try:
        invoice = await service.link_to_billing(params.invoice_id, params.billing_id)
        return SuccessResponse(data=invoice, message="發票已關聯到此請款")
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
