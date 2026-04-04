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


@router.post("/financial-overview")
async def financial_overview(
    request: Request,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """全案件財務總覽 — 主管/財務視角

    整合所有案件的 billing(應收) + vendor_payable(應付) + expense(核銷)。
    """
    from sqlalchemy import select, func, case as sa_case
    from app.extended.models.erp import ERPQuotation, ERPBilling, ERPInvoice, ERPVendorPayable
    from app.extended.models.invoice import ExpenseInvoice

    # 1. 應收 (billings) 按案件分組
    billing_stmt = (
        select(
            ERPQuotation.case_code,
            ERPQuotation.case_name,
            ERPQuotation.project_code,
            func.count(ERPBilling.id).label("billing_count"),
            func.sum(ERPBilling.billing_amount).label("billing_total"),
            func.sum(sa_case(
                (ERPBilling.payment_status == "paid", ERPBilling.billing_amount), else_=0
            )).label("billing_received"),
        )
        .join(ERPBilling, ERPBilling.erp_quotation_id == ERPQuotation.id)
        .group_by(ERPQuotation.case_code, ERPQuotation.case_name, ERPQuotation.project_code)
    )
    billing_result = await service.db.execute(billing_stmt)
    billing_rows = {r.case_code: r for r in billing_result.all()}

    # 2. 應付 (vendor_payables) 按案件分組
    payable_stmt = (
        select(
            ERPQuotation.case_code,
            func.count(ERPVendorPayable.id).label("payable_count"),
            func.sum(ERPVendorPayable.payable_amount).label("payable_total"),
            func.sum(sa_case(
                (ERPVendorPayable.payment_status == "paid", ERPVendorPayable.payable_amount), else_=0
            )).label("payable_paid"),
        )
        .join(ERPVendorPayable, ERPVendorPayable.erp_quotation_id == ERPQuotation.id)
        .group_by(ERPQuotation.case_code)
    )
    payable_result = await service.db.execute(payable_stmt)
    payable_rows = {r.case_code: r for r in payable_result.all()}

    # 3. 費用核銷按案件分組
    expense_stmt = (
        select(
            ExpenseInvoice.case_code,
            func.count(ExpenseInvoice.id).label("expense_count"),
            func.sum(ExpenseInvoice.amount).label("expense_total"),
            func.sum(sa_case(
                (ExpenseInvoice.status == "verified", ExpenseInvoice.amount), else_=0
            )).label("expense_verified"),
            func.sum(sa_case(
                (ExpenseInvoice.status.in_(["pending", "manager_approved", "finance_approved"]),
                 ExpenseInvoice.amount), else_=0
            )).label("expense_pending"),
        )
        .where(ExpenseInvoice.case_code.isnot(None))
        .group_by(ExpenseInvoice.case_code)
    )
    expense_result = await service.db.execute(expense_stmt)
    expense_rows = {r.case_code: r for r in expense_result.all()}

    # 4. 合併所有案件
    all_codes = set(billing_rows.keys()) | set(payable_rows.keys()) | set(expense_rows.keys())
    cases = []
    totals = {"billing": 0, "billing_received": 0, "payable": 0, "payable_paid": 0,
              "expense": 0, "expense_verified": 0, "expense_pending": 0}

    for code in sorted(all_codes):
        b = billing_rows.get(code)
        p = payable_rows.get(code)
        e = expense_rows.get(code)

        row = {
            "case_code": code,
            "case_name": b.case_name if b else None,
            "project_code": b.project_code if b else None,
            "billing_count": b.billing_count if b else 0,
            "billing_total": float(b.billing_total or 0) if b else 0,
            "billing_received": float(b.billing_received or 0) if b else 0,
            "payable_count": p.payable_count if p else 0,
            "payable_total": float(p.payable_total or 0) if p else 0,
            "payable_paid": float(p.payable_paid or 0) if p else 0,
            "expense_count": e.expense_count if e else 0,
            "expense_total": float(e.expense_total or 0) if e else 0,
            "expense_verified": float(e.expense_verified or 0) if e else 0,
            "expense_pending": float(e.expense_pending or 0) if e else 0,
        }
        cases.append(row)
        totals["billing"] += row["billing_total"]
        totals["billing_received"] += row["billing_received"]
        totals["payable"] += row["payable_total"]
        totals["payable_paid"] += row["payable_paid"]
        totals["expense"] += row["expense_total"]
        totals["expense_verified"] += row["expense_verified"]
        totals["expense_pending"] += row["expense_pending"]

    # 5. 未歸案費用
    unlinked_stmt = (
        select(
            func.count(ExpenseInvoice.id).label("count"),
            func.sum(ExpenseInvoice.amount).label("total"),
        )
        .where(ExpenseInvoice.case_code.is_(None))
    )
    unlinked = await service.db.execute(unlinked_stmt)
    unlinked_row = unlinked.first()

    return SuccessResponse(data={
        "cases": cases,
        "totals": totals,
        "unlinked_expenses": {
            "count": unlinked_row.count if unlinked_row else 0,
            "total": float(unlinked_row.total or 0) if unlinked_row else 0,
        },
    })


@router.post("/case-finance")
async def case_finance_summary(
    request: Request,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """案件整合財務紀錄 — 整合 expense_invoices + erp_billings + erp_invoices

    用於 PM Case 費用 Tab，一次取得該案件所有財務相關紀錄。
    """
    body = await request.json()
    case_code = body.get("case_code")
    if not case_code:
        raise HTTPException(status_code=400, detail="case_code 為必填")

    from sqlalchemy import select, func
    from app.extended.models.invoice import ExpenseInvoice
    from app.extended.models.erp import ERPQuotation, ERPBilling, ERPInvoice

    # 1. 費用報銷
    exp_result = await service.db.execute(
        select(ExpenseInvoice).where(ExpenseInvoice.case_code == case_code)
        .order_by(ExpenseInvoice.date.desc()).limit(100)
    )
    expenses = [
        {"type": "expense", "id": e.id, "date": str(e.date) if e.date else None,
         "amount": float(e.amount or 0), "description": e.inv_num,
         "category": e.category, "status": e.status, "source": e.source}
        for e in exp_result.scalars().all()
    ]

    # 2. ERP 請款 + 開票 (via erp_quotation)
    q_result = await service.db.execute(
        select(ERPQuotation.id).where(ERPQuotation.case_code == case_code)
    )
    q_ids = [r[0] for r in q_result.all()]

    billings = []
    invoices = []
    if q_ids:
        b_result = await service.db.execute(
            select(ERPBilling).where(ERPBilling.erp_quotation_id.in_(q_ids))
            .order_by(ERPBilling.billing_date.desc())
        )
        billings = [
            {"type": "billing", "id": b.id, "date": str(b.billing_date) if b.billing_date else None,
             "amount": float(b.billing_amount or 0), "description": b.billing_period or "請款",
             "category": "請款", "status": b.payment_status, "source": "erp_billing"}
            for b in b_result.scalars().all()
        ]

        i_result = await service.db.execute(
            select(ERPInvoice).where(ERPInvoice.erp_quotation_id.in_(q_ids))
            .order_by(ERPInvoice.invoice_date.desc())
        )
        invoices = [
            {"type": "invoice", "id": inv.id, "date": str(inv.invoice_date) if inv.invoice_date else None,
             "amount": float(inv.amount or 0), "description": inv.invoice_number or "發票",
             "category": "開票", "status": "issued", "source": "erp_invoice"}
            for inv in i_result.scalars().all()
        ]

    all_records = expenses + billings + invoices
    all_records.sort(key=lambda x: x.get("date") or "", reverse=True)

    return SuccessResponse(data={
        "case_code": case_code,
        "records": all_records,
        "summary": {
            "expense_count": len(expenses),
            "expense_total": sum(e["amount"] for e in expenses),
            "billing_count": len(billings),
            "billing_total": sum(b["amount"] for b in billings),
            "invoice_count": len(invoices),
            "invoice_total": sum(i["amount"] for i in invoices),
        },
    })


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
        return SuccessResponse(data=ExpenseInvoiceResponse.model_validate(result), message="報銷發票建立成功")
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
        return SuccessResponse(data=ExpenseInvoiceResponse.model_validate(result), message="已駁回")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delete")
async def delete_expense(
    params: ERPIdRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_permission("projects:write")),
):
    """刪除費用核銷紀錄（僅 pending/rejected 狀態可刪）"""
    try:
        await service.delete_expense(params.id)
        return SuccessResponse(data=None, message="已刪除")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
