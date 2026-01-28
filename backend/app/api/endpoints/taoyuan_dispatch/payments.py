"""
桃園派工系統 - 契金管控 API

包含端點：
- /payments/list - 契金管控列表
- /payments/create - 建立契金管控
- /payments/{payment_id}/update - 更新契金管控
- /payments/control - 契金管控展示

@version 2.0.0 - 重構使用 Service Layer
@date 2026-01-28
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from .common import (
    get_async_db, require_auth,
    ContractPaymentCreate, ContractPaymentUpdate, ContractPaymentSchema,
    ContractPaymentListResponse, PaymentControlResponse,
    PaginationMeta
)
from app.services.taoyuan import PaymentService

router = APIRouter()


def get_payment_service(db: AsyncSession = Depends(get_async_db)) -> PaymentService:
    """依賴注入：取得 PaymentService"""
    return PaymentService(db)


@router.post("/payments/list", response_model=ContractPaymentListResponse, summary="契金管控列表")
async def list_contract_payments(
    dispatch_order_id: Optional[int] = Body(None),
    contract_project_id: Optional[int] = Body(None),
    page: int = Body(1),
    limit: int = Body(20),
    service: PaymentService = Depends(get_payment_service),
    current_user = Depends(require_auth())
):
    """查詢契金管控列表"""
    items, total = await service.list_payments(
        dispatch_order_id=dispatch_order_id,
        contract_project_id=contract_project_id,
        page=page,
        limit=limit
    )

    total_pages = (total + limit - 1) // limit

    return ContractPaymentListResponse(
        success=True,
        items=[ContractPaymentSchema(**item) for item in items],
        pagination=PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    )


@router.post("/payments/create", response_model=ContractPaymentSchema, summary="建立契金管控")
async def create_contract_payment(
    data: ContractPaymentCreate,
    service: PaymentService = Depends(get_payment_service),
    current_user = Depends(require_auth)
):
    """建立契金管控記錄"""
    payment = await service.create_payment(data)
    if not payment:
        raise HTTPException(status_code=404, detail="派工紀錄不存在")
    return ContractPaymentSchema.model_validate(payment)


@router.post("/payments/{payment_id}/update", response_model=ContractPaymentSchema, summary="更新契金管控")
async def update_contract_payment(
    payment_id: int,
    data: ContractPaymentUpdate,
    service: PaymentService = Depends(get_payment_service),
    current_user = Depends(require_auth)
):
    """更新契金管控記錄"""
    payment = await service.update_payment(payment_id, data)
    if not payment:
        raise HTTPException(status_code=404, detail="契金管控記錄不存在")
    return ContractPaymentSchema.model_validate(payment)


@router.post("/payments/control", response_model=PaymentControlResponse, summary="契金管控展示")
async def get_payment_control(
    contract_project_id: Optional[int] = Body(None),
    page: int = Body(1),
    limit: int = Body(100),
    service: PaymentService = Depends(get_payment_service),
    current_user = Depends(require_auth())
):
    """取得契金管控展示資料"""
    result = await service.get_payment_control_report(
        contract_project_id=contract_project_id,
        page=page,
        limit=limit
    )

    total_pages = (result['total'] + limit - 1) // limit

    return PaymentControlResponse(
        success=True,
        items=result['items'],
        total_budget=result['total_budget'],
        total_dispatched=result['total_dispatched'],
        total_remaining=result['total_remaining'],
        pagination=PaginationMeta(
            total=result['total'],
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    )
