"""費用報銷 CRUD 端點 — 列表/新增/修改/審核

IO 相關端點 (QR/OCR/匯入匯出/收據/AI) 已拆分至 expenses_io.py
"""
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.dependencies import get_service, optional_auth, require_auth, require_permission
from app.extended.models import User
from app.services.expense_invoice_service import ExpenseInvoiceService
from app.schemas.erp.expense import (
    ExpenseInvoiceCreate,
    ExpenseInvoiceQuery,
    ExpenseInvoiceResponse,
    ExpenseInvoiceUpdateRequest,
    ExpenseInvoiceRejectRequest,
)
from app.schemas.erp.requests import ERPIdRequest
from app.schemas.common import PaginatedResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/list")
async def list_expenses(
    params: ExpenseInvoiceQuery,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """費用發票列表 (多條件查詢)"""
    items, total = await service.query(params)
    return PaginatedResponse.create(
        items=[ExpenseInvoiceResponse.model_validate(i) for i in items],
        total=total, page=(params.skip // params.limit) + 1, limit=params.limit
    )


@router.post("/grouped-summary")
async def grouped_expense_summary(
    request: Request,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """費用核銷按歸屬分組彙總 — 專案/營運/未歸屬各自統計"""
    body = await request.json()
    attribution_type = body.get("attribution_type")
    result = await service.grouped_summary(attribution_type=attribution_type)
    return SuccessResponse(data=result)


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
    current_user: User = Depends(require_auth()),
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
    current_user: User = Depends(require_auth()),
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
    current_user: User = Depends(require_permission("projects:write")),
):
    """多層審核推進 — 依金額自動決定下一審核階段

    預算聯防：即將 verified 時自動比對專案預算
    - >100%: 攔截 (HTTP 400)
    - >80%: 警告 (附在 message 中，仍放行)
    """
    try:
        result = await service.approve(params.id)
        if not result:
            raise HTTPException(status_code=404, detail="發票不存在")

        budget_warning = getattr(result, '_budget_warning', None)
        msg = "審核通過"
        if budget_warning:
            msg += f" | {budget_warning}"

        approval_info = ExpenseInvoiceService.get_approval_info(result)
        return SuccessResponse(
            data={
                "invoice": ExpenseInvoiceResponse.model_validate(result),
                "approval_info": approval_info,
                "budget_warning": budget_warning,
            },
            message=msg,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reject")
async def reject_expense(
    params: ExpenseInvoiceRejectRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_permission("projects:write")),
):
    """駁回報銷"""
    try:
        result = await service.reject(params.id, reason=params.reason)
        if not result:
            raise HTTPException(status_code=404, detail="發票不存在")
        return SuccessResponse(data=result, message="已駁回")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
