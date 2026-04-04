"""營運帳目 API 端點 (POST-only)

帳目 CRUD + 費用 CRUD + 統計
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service, require_auth, optional_auth
from app.extended.models import User
from app.services.erp.operational_service import OperationalAccountService
from app.schemas.erp.operational import (
    OperationalAccountCreate,
    OperationalAccountUpdate,
    OperationalAccountUpdateRequest,
    OperationalAccountListRequest,
    OperationalAccountResponse,
    OperationalExpenseCreate,
    OperationalExpenseListRequest,
    OperationalExpenseResponse,
    OperationalExpenseApproveRequest,
    OperationalExpenseRejectRequest,
)
from app.schemas.erp.requests import ERPIdRequest
from app.schemas.common import PaginatedResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Account Endpoints
# ============================================================================

@router.post("/list")
async def list_accounts(
    params: OperationalAccountListRequest,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """營運帳目列表"""
    items, total = await service.list_accounts(params)
    return PaginatedResponse.create(
        items=[OperationalAccountResponse.model_validate(i) for i in items],
        total=total,
        page=(params.skip // params.limit) + 1, limit=params.limit,
    )


@router.post("/create")
async def create_account(
    data: OperationalAccountCreate,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """建立營運帳目 (自動產生編號)"""
    try:
        result = await service.create_account(data, user_id=current_user.id)
        return SuccessResponse(data=result, message="營運帳目建立成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/detail")
async def get_account_detail(
    params: ERPIdRequest,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """營運帳目詳情"""
    result = await service.get_account(params.id)
    if not result:
        raise HTTPException(status_code=404, detail="帳目不存在")
    return SuccessResponse(data=result)


@router.post("/update")
async def update_account(
    params: OperationalAccountUpdateRequest,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """更新營運帳目"""
    try:
        result = await service.update_account(params.id, params.data)
        if not result:
            raise HTTPException(status_code=404, detail="帳目不存在")
        return SuccessResponse(data=result, message="更新成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delete")
async def delete_account(
    params: ERPIdRequest,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """刪除營運帳目"""
    result = await service.delete_account(params.id)
    if not result:
        raise HTTPException(status_code=404, detail="帳目不存在")
    return SuccessResponse(message="刪除成功")


@router.post("/stats")
async def get_stats(
    params: dict = {},
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """營運帳目統計"""
    fiscal_year = params.get("fiscal_year") if isinstance(params, dict) else None
    result = await service.get_stats(fiscal_year=fiscal_year)
    return SuccessResponse(data=result)


# ============================================================================
# Expense Endpoints
# ============================================================================

@router.post("/expenses/list")
async def list_expenses(
    params: OperationalExpenseListRequest,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """營運費用列表"""
    items, total = await service.list_expenses(params)
    return PaginatedResponse.create(
        items=[OperationalExpenseResponse.model_validate(i) for i in items],
        total=total,
        page=(params.skip // params.limit) + 1, limit=params.limit,
    )


@router.post("/expenses/create")
async def create_expense(
    data: OperationalExpenseCreate,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """建立營運費用"""
    try:
        result = await service.create_expense(data, user_id=current_user.id)
        return SuccessResponse(data=result, message="費用建立成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/expenses/approve")
async def approve_expense(
    params: OperationalExpenseApproveRequest,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """核准營運費用"""
    result = await service.approve_expense(params.id, approved_by=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="費用不存在或非待審狀態")
    return SuccessResponse(data=result, message="核准成功")


@router.post("/expenses/reject")
async def reject_expense(
    params: OperationalExpenseRejectRequest,
    service: OperationalAccountService = Depends(get_service(OperationalAccountService)),
    current_user: User = Depends(require_auth()),
):
    """駁回營運費用"""
    result = await service.reject_expense(params.id, reason=params.reason)
    if not result:
        raise HTTPException(status_code=404, detail="費用不存在或非待審狀態")
    return SuccessResponse(data=result, message="已駁回")
