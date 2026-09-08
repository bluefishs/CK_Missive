"""費用報銷 CRUD 端點 — 列表/新增/修改/審核

IO 相關端點 (QR/OCR/匯入匯出/收據/AI) 已拆分至 expenses_io.py
"""
from app.core.roc_date import roc_year_to_ad
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.dependencies import get_service, optional_auth, require_auth, require_permission
from app.core.case_scope import assert_case_scope, scope_filter, has_company_wide_scope
from app.extended.models import User
from app.services.erp.expense_invoice import ExpenseInvoiceService
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
    # 2026-09-08 owner：「給 staff，並把列表也限縮到自己的案」。
    # 「看得到」與「動得了」用同一個口徑 —— 只擋動作的話，業務同仁打開這一頁
    # 仍會看到全公司每一筆核銷的金額與明細，管控只做了一半。
    items, total = await service.query(
        params, scope_case_codes=await scope_filter(service.db, current_user),
    )
    # 2026-08-17：一次查出人名（不在迴圈裡逐筆查 —— 那是 N+1）
    people = await service.attach_people(items)
    responses = []
    for i in items:
        resp = ExpenseInvoiceResponse.model_validate(i)
        info = service.get_approval_info(i)
        resp.approval_level = info.get("approval_level")
        resp.next_approval = info.get("next_approval")
        resp.uploader_name = people.get(getattr(i, "user_id", None))
        resp.approved_by_name = people.get(getattr(i, "approved_by", None))
        responses.append(resp)
    return PaginatedResponse.create(
        items=responses,
        total=total, page=(params.skip // params.limit) + 1, limit=params.limit
    )


@router.post("/grouped-summary")
async def grouped_expense_summary(
    request: Request,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """費用核銷按歸屬分組彙總 — 專案/營運/未歸屬各自統計"""
    # 2026-09-08：這一支以 **erp_quotations 全量案件**為基底（見 service.grouped_summary
    # 的說明），是跨案彙總不是我的案 ⇒ 與 financial-overview 同一個處置。
    if not has_company_wide_scope(current_user):
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException(
            "分組彙總是跨全案件的統計，僅限管理者／高階主管／財務檢視。"
        )
    body = await request.json()
    attribution_type = body.get("attribution_type")
    # 2026-08-29 owner 裁示：統計以當年度為基準。年度一律西元（§2.5）；
    # 收到 <1911 視為舊客戶端送民國年，轉換並出聲不靜默接受。
    year = body.get("year")
    if isinstance(year, int) and 0 < year < 1911:
        logger.warning(
            "grouped-summary 收到民國年 %s —— 系統已統一西元（§2.5），"
            "請修正呼叫端；本次轉換為 %s", year, roc_year_to_ad(year),
        )
        year = roc_year_to_ad(year)
    result = await service.grouped_summary(
        attribution_type=attribution_type, year=year,
    )
    return SuccessResponse(data=result)


@router.post("/financial-overview")
async def financial_overview(
    request: Request,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """全案件財務總覽 — 主管/財務視角

    整合所有案件的 billing(應收) + vendor_payable(應付) + expense(核銷)。
    2026-07-20 DDD 標準化：聚合邏輯委派 ExpenseInvoiceService（原端點內直 SQL）。
    """
    # ⭐ 2026-09-08：這一支的 docstring 自己就寫著「主管/財務視角」，而它是
    # **跨全公司**的彙總（不是某一案）。把 `/erp/expenses` 開給 staff 之後，
    # 若不另外擋，業務同仁會連全公司的應收／應付／核銷總覽一起拿到。
    # ⇒ 與 `/erp/invoices/summary` 同一個處置：頁面權限放寬、跨案彙總另外守。
    # 限縮成「我的案的總覽」則會改變它的語意（那個數字比不限縮更容易誤導，
    # 同 2026-08-31 對委託／協力帳款「維持全公司視角、改用權限區分」的裁示）。
    if not has_company_wide_scope(current_user):
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException(
            "全案件財務總覽是全公司彙總，僅限管理者／高階主管／財務檢視。"
            "你可以在費用核銷列表看到自己承辦案件的明細。"
        )
    return SuccessResponse(data=await service.get_financial_overview())


@router.post("/create")
async def create_expense(
    data: ExpenseInvoiceCreate,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(optional_auth()),
):
    """建立報銷發票"""
    user_id = current_user.id if current_user else None
    # 只有「業務規則衝突」（重複憑證 / case_code 不存在）才是 409。
    # 2026-07-30：原本 model_validate 也在 try 內，而 pydantic ValidationError 是
    # **ValueError 子類** → 序列化失敗被誤報成「409 憑證重複」，且此時資料已 commit
    # → 使用者以為存檔失敗、重試又撞真重複，症狀一致到掩蓋真因。
    # 故序列化移出 try，另行處理並 LOUD（ADR-0028 去 silent/去誤標）。
    try:
        result = await service.create(data, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    try:
        payload = ExpenseInvoiceResponse.model_validate(result)
    except Exception as e:
        logger.error(
            "報銷發票已建立（id=%s）但回應序列化失敗 — 資料已存檔，勿重試建立: %s",
            getattr(result, "id", None), e, exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"紀錄已建立（編號 {getattr(result, 'inv_num', '')}），"
                "但回應資料組裝失敗；請重新整理列表確認，勿重複送出。"
            ),
        )
    return SuccessResponse(data=payload, message="報銷發票建立成功")


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
    # 2026-09-08：列表限縮了而詳情不擋，等於留下「知道 id 就看得到」的旁路 ——
    # 那是本 repo 記過的「換出口沒換整條路」。用與列表同一個口徑。
    await assert_case_scope(service.db, current_user, [result.case_code], "檢視")
    return SuccessResponse(data=ExpenseInvoiceResponse.model_validate(result))


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
    return SuccessResponse(data=ExpenseInvoiceResponse.model_validate(result), message="更新成功")


@router.post("/approve")
async def approve_expense(
    params: ERPIdRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_permission("projects:edit")),
):
    """多層審核推進 — 依金額自動決定下一審核階段

    預算聯防：即將 verified 時自動比對專案預算
    - >100%: 攔截 (HTTP 400)
    - >80%: 警告 (附在 message 中，仍放行)
    """
    # ⭐ 2026-09-08 owner：「projects:write 重點要對能對應承辦同仁案件，以利管控」。
    # 權限碼只回答「等級夠不夠」，範圍要另外問：這筆核銷的案子是不是我承辦的。
    # 先查再動 —— 查不到就是 404，範圍不符就是 403，兩者要分得開。
    target = await service.get_by_id(params.id)
    if not target:
        raise HTTPException(status_code=404, detail="發票不存在")
    await assert_case_scope(service.db, current_user, [target.case_code], "審核")
    try:
        result = await service.approve(params.id, approver_id=current_user.id)
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


@router.post("/batch-approve")
async def batch_approve_expenses(
    request: Request,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_permission("projects:edit")),
):
    """批次審核 — 多筆同時推進至下一審核階段

    Request body: {"ids": [1, 2, 3]}
    """
    body = await request.json()
    ids = body.get("ids", [])
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids 為必填陣列")
    if len(ids) > 50:
        raise HTTPException(status_code=400, detail="單次最多 50 筆")

    # 批次要在動之前**整批**驗範圍：逐筆放行會讓批次變成繞過單筆守衛的後門。
    targets = [await service.get_by_id(i) for i in ids]
    await assert_case_scope(
        service.db, current_user,
        [t.case_code for t in targets if t is not None], "審核",
    )

    results = {"success": [], "failed": []}
    for invoice_id in ids:
        try:
            result = await service.approve(invoice_id, approver_id=current_user.id)
            if result:
                results["success"].append({"id": invoice_id, "new_status": result.status})
            else:
                results["failed"].append({"id": invoice_id, "error": "不存在"})
        except ValueError as e:
            results["failed"].append({"id": invoice_id, "error": str(e)})

    return SuccessResponse(
        data=results,
        message=f"批次審核完成: {len(results['success'])} 成功, {len(results['failed'])} 失敗",
    )


@router.post("/reject")
async def reject_expense(
    params: ExpenseInvoiceRejectRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_permission("projects:edit")),
):
    """駁回報銷"""
    target = await service.get_by_id(params.id)
    if not target:
        raise HTTPException(status_code=404, detail="發票不存在")
    await assert_case_scope(service.db, current_user, [target.case_code], "駁回")
    try:
        result = await service.reject(params.id, reason=params.reason)
        if not result:
            raise HTTPException(status_code=404, detail="發票不存在")
        return SuccessResponse(data=ExpenseInvoiceResponse.model_validate(result), message="已駁回")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delete")
async def delete_expense(
    params: ERPIdRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_permission("projects:edit")),
):
    """刪除費用核銷紀錄（僅 pending/rejected 狀態可刪）"""
    target = await service.get_by_id(params.id)
    if not target:
        raise HTTPException(status_code=404, detail="發票不存在")
    await assert_case_scope(service.db, current_user, [target.case_code], "刪除")
    try:
        await service.delete_expense(params.id)
        return SuccessResponse(data=None, message="已刪除")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
