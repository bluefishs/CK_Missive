"""費用報銷發票 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service, optional_auth
from app.extended.models import User
from app.services.expense_invoice_service import ExpenseInvoiceService
from app.schemas.erp.expense import (
    ExpenseInvoiceCreate,
    ExpenseInvoiceQuery,
    ExpenseInvoiceUpdateRequest,
    ExpenseInvoiceRejectRequest,
    ExpenseInvoiceQRScanRequest,
)
from app.schemas.erp.requests import ERPIdRequest
from app.schemas.common import PaginatedResponse, SuccessResponse

router = APIRouter()


@router.post("/list")
async def list_expenses(
    params: ExpenseInvoiceQuery,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
):
    """費用發票列表 (多條件查詢)"""
    items, total = await service.query(params)
    return PaginatedResponse.create(
        items=items, total=total, page=(params.skip // params.limit) + 1, limit=params.limit
    )


@router.post("/create")
async def create_expense(
    data: ExpenseInvoiceCreate,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(optional_auth()),
):
    """建立報銷發票"""
    try:
        user_id = current_user.id if current_user else None
        result = await service.create(data, user_id=user_id)
        return SuccessResponse(data=result, message="報銷發票建立成功")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/detail")
async def get_expense_detail(
    params: ERPIdRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
):
    """取得發票詳情"""
    result = await service.get_by_id(params.id)
    if not result:
        raise HTTPException(status_code=404, detail="發票不存在")
    return SuccessResponse(data=result)


@router.post("/update")
async def update_expense(
    params: ExpenseInvoiceUpdateRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
):
    """更新報銷發票"""
    result = await service.update(params.id, params.data)
    if not result:
        raise HTTPException(status_code=404, detail="發票不存在")
    return SuccessResponse(data=result, message="更新成功")


@router.post("/approve")
async def approve_expense(
    params: ERPIdRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
):
    """審核通過 (自動寫入帳本)"""
    try:
        result = await service.approve(params.id)
        if not result:
            raise HTTPException(status_code=404, detail="發票不存在")
        return SuccessResponse(data=result, message="審核通過，已自動入帳")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reject")
async def reject_expense(
    params: ExpenseInvoiceRejectRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
):
    """駁回報銷"""
    try:
        result = await service.reject(params.id, reason=params.reason)
        if not result:
            raise HTTPException(status_code=404, detail="發票不存在")
        return SuccessResponse(data=result, message="已駁回")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/qr-scan")
async def create_from_qr(
    params: ExpenseInvoiceQRScanRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(optional_auth()),
):
    """QR Code 掃描建立報銷發票"""
    try:
        user_id = current_user.id if current_user else None
        result = await service.create_from_qr(
            raw_qr=params.raw_qr,
            case_code=params.case_code,
            category=params.category,
            user_id=user_id,
        )
        return SuccessResponse(data=result, message="QR 發票建立成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
