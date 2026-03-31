"""ERP 廠商帳款查詢 API — 跨案件應付彙總 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.repositories.erp.vendor_payable_repository import ERPVendorPayableRepository
from app.schemas.erp.vendor_financial import (
    VendorAccountListRequest,
    VendorAccountDetailRequest,
)
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.post("/summary")
async def get_vendor_account_summary(
    params: VendorAccountListRequest,
    repo: ERPVendorPayableRepository = Depends(get_service(ERPVendorPayableRepository)),
):
    """協力廠商跨案件應付彙總列表"""
    items, total = await repo.get_vendor_summary_list(
        vendor_type=params.vendor_type,
        year=params.year,
        keyword=params.keyword,
        skip=params.skip,
        limit=params.limit,
    )
    return SuccessResponse(data={"items": items, "total": total})


@router.post("/detail")
async def get_vendor_account_detail(
    params: VendorAccountDetailRequest,
    repo: ERPVendorPayableRepository = Depends(get_service(ERPVendorPayableRepository)),
):
    """單一廠商跨案件應付明細"""
    result = await repo.get_vendor_case_detail(
        vendor_id=params.vendor_id, year=params.year,
    )
    if not result:
        raise HTTPException(status_code=404, detail="廠商不存在")
    return SuccessResponse(data=result)
