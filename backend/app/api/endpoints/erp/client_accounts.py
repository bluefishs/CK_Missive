"""ERP 委託單位帳款查詢 API — 跨案件應收彙總 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.repositories.erp.client_receivable_repository import ClientReceivableRepository
from app.schemas.erp.vendor_financial import (
    ClientAccountListRequest,
    VendorAccountDetailRequest,
)
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.post("/summary")
async def get_client_account_summary(
    params: ClientAccountListRequest,
    repo: ClientReceivableRepository = Depends(get_service(ClientReceivableRepository)),
):
    """委託單位跨案件應收彙總列表"""
    items, total = await repo.get_client_summary_list(
        year=params.year,
        keyword=params.keyword,
        skip=params.skip,
        limit=params.limit,
    )
    return SuccessResponse(data={"items": items, "total": total})


@router.post("/detail")
async def get_client_account_detail(
    params: VendorAccountDetailRequest,
    repo: ClientReceivableRepository = Depends(get_service(ClientReceivableRepository)),
):
    """單一委託單位跨案件應收明細"""
    result = await repo.get_client_case_detail(
        vendor_id=params.vendor_id, year=params.year,
    )
    if not result:
        raise HTTPException(status_code=404, detail="委託單位不存在")
    return SuccessResponse(data=result)
