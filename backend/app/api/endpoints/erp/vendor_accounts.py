"""ERP 廠商帳款查詢 API — 跨案件應付彙總 (POST-only)

⭐ 2026-09-08 owner：「/erp/client-accounts 及 /erp/vendor-accounts 尚無對應
登入帳號對應篩選委託與協力單位帳款機制（登入者 業務同仁王駿穠）」。

實測：這兩頁此前**完全不看登入身分** —— 業務同仁打開就是全公司
（協力 19 家、應付 1,367 萬），含別人承辦的案。
而 `/erp/quotations` 09-08 早上已依身分限縮 ⇒
**同一條規則有兩個實作，改了一個沒改另一個**（L145 家族）。

範圍走既有的 `case_scope.scope_filter`（不另寫一份判定）：
admin／exec／finance／superuser 是全公司視角回 `None`（不限縮），
其餘只看自己承辦的案。⚠️ 明細端點一併限縮 ——
列表擋了而明細沒擋，等於用網址就繞過去。
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service, get_async_db, require_auth
from app.core.case_scope import scope_filter
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
    db=Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """協力廠商跨案件應付彙總列表（依登入身分限縮）"""
    scope = await scope_filter(db, current_user)
    items, total, totals = await repo.get_vendor_summary_list(
        accessible_case_codes=scope,
        vendor_type=params.vendor_type,
        year=params.year,
        keyword=params.keyword,
        staff_user_id=params.staff_user_id,
        category=params.category,
        skip=params.skip,
        limit=params.limit,
    )
    # totals＝分頁前的全量合計（§2.6 ①：卡片的分母不是當頁）
    return SuccessResponse(data={"items": items, "total": total, "totals": totals})


@router.post("/detail")
async def get_vendor_account_detail(
    params: VendorAccountDetailRequest,
    repo: ERPVendorPayableRepository = Depends(get_service(ERPVendorPayableRepository)),
    db=Depends(get_async_db),
    current_user=Depends(require_auth()),
):
    """單一廠商跨案件應付明細（依登入身分限縮）"""
    scope = await scope_filter(db, current_user)
    result = await repo.get_vendor_case_detail(
        vendor_id=params.vendor_id, year=params.year,
        accessible_case_codes=scope,
    )
    if not result:
        raise HTTPException(status_code=404, detail="廠商不存在")
    return SuccessResponse(data=result)
