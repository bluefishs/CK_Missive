"""案件整合財務紀錄（`/erp/expenses/case-finance`）—— 從 `expenses.py` 拆出。

⭐ 2026-09-08：拆檔的理由是**權限，不是程式碼長度**。

`expenses.py` 其餘 10 支是「費用報銷」本身（列表／建立／**審核**／退回／刪除／
全公司財務總覽），屬於 `/erp/expenses` 那一頁，門檻是 `reports:expenses:view`
（staff 沒有，這是對的 —— 審核權不該人人有）。

而這一支是**案件頁面上的分頁在用的**：報價單詳情與 PM 案件詳情各有一個
「費用」分頁，兩者都只呼叫它（實查 `pages/erpQuotation/ExpensesTab.tsx` 與
`pages/pmCase/ExpensesTab.tsx`，各自唯一的端點常數就是 `EXPENSES_CASE_FINANCE`）。
掛在 `/erp/expenses` 之下 ⇒ **每個承辦打開自己案件的費用分頁都是 403**
（09-08 owner 的瀏覽器 console 實證）。

修法選項有兩個：把 router 層改成聯集（但那會連審核、全公司總覽一起放寬），
或把這一支拆出來單獨掛聯集。選後者 —— **放寬的範圍要剛好等於問題的範圍。**
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.dependencies import get_service, require_auth
from app.extended.models import User
from app.services.erp.expense_invoice import ExpenseInvoiceService
from app.schemas.erp.expense import CaseFinanceResponse
from app.schemas.common import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/case-finance", response_model=SuccessResponse[CaseFinanceResponse])
async def case_finance_summary(
    request: Request,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """案件整合財務紀錄 — 整合 expense_invoices + erp_billings + erp_invoices

    用於 PM Case 費用 Tab，一次取得該案件所有財務相關紀錄。
    2026-07-20 DDD 標準化：聚合邏輯委派 ExpenseInvoiceService（原端點內直 SQL）。
    """
    body = await request.json()
    case_code = body.get("case_code")
    if not case_code:
        raise HTTPException(status_code=400, detail="case_code 為必填")
    # 2026-07-31：綁 response_model 讓契約有單一來源 —— 前端兩個 ExpensesTab
    # 原本各自宣告一份同名 interface，後端改欄位不會有人發現。
    return SuccessResponse[CaseFinanceResponse](
        data=CaseFinanceResponse.model_validate(await service.get_case_finance(case_code))
    )
