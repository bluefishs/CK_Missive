"""統一帳本 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service, optional_auth, require_auth
from app.extended.models import User
from app.services.finance_ledger_service import FinanceLedgerService
from app.schemas.erp.ledger import (
    LedgerCreate,
    LedgerQuery,
    LedgerBalanceRequest,
    LedgerCategoryBreakdownRequest,
)
from app.schemas.erp.requests import ERPIdRequest
from app.schemas.common import PaginatedResponse, SuccessResponse

router = APIRouter()


@router.post("/list")
async def list_ledger(
    params: LedgerQuery,
    service: FinanceLedgerService = Depends(get_service(FinanceLedgerService)),
    current_user: User = Depends(require_auth()),
):
    """帳本記錄列表 (多條件查詢)"""
    items, total = await service.query(params)
    return PaginatedResponse.create(
        items=items, total=total, page=(params.skip // params.limit) + 1, limit=params.limit
    )


@router.post("/create")
async def create_ledger_entry(
    data: LedgerCreate,
    service: FinanceLedgerService = Depends(get_service(FinanceLedgerService)),
    current_user: User = Depends(optional_auth()),
):
    """手動記帳"""
    user_id = current_user.id if current_user else None
    result = await service.create(data, user_id=user_id)
    return SuccessResponse(data=result, message="記帳成功")


@router.post("/detail")
async def get_ledger_detail(
    params: ERPIdRequest,
    service: FinanceLedgerService = Depends(get_service(FinanceLedgerService)),
    current_user: User = Depends(require_auth()),
):
    """取得帳本記錄詳情"""
    result = await service.get_by_id(params.id)
    if not result:
        raise HTTPException(status_code=404, detail="帳本記錄不存在")
    return SuccessResponse(data=result)


@router.post("/balance")
async def get_case_balance(
    params: LedgerBalanceRequest,
    service: FinanceLedgerService = Depends(get_service(FinanceLedgerService)),
    current_user: User = Depends(require_auth()),
):
    """查詢專案收支餘額"""
    result = await service.get_case_balance(params.case_code)
    return SuccessResponse(data=result)


@router.post("/category-breakdown")
async def get_category_breakdown(
    params: LedgerCategoryBreakdownRequest,
    service: FinanceLedgerService = Depends(get_service(FinanceLedgerService)),
    current_user: User = Depends(require_auth()),
):
    """帳本分類拆解"""
    result = await service.get_category_breakdown(
        case_code=params.case_code,
        date_from=params.date_from,
        date_to=params.date_to,
        entry_type=params.entry_type,
    )
    return SuccessResponse(data=result)


@router.post("/delete")
async def delete_ledger_entry(
    params: ERPIdRequest,
    service: FinanceLedgerService = Depends(get_service(FinanceLedgerService)),
    current_user: User = Depends(require_auth()),
):
    """刪除帳本記錄 (僅限手動記帳)"""
    try:
        success = await service.delete(params.id)
        if not success:
            raise HTTPException(status_code=404, detail="帳本記錄不存在")
        return SuccessResponse(message="刪除成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
