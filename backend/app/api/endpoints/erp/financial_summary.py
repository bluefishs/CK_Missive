"""跨模組財務彙總 API 端點 (POST-only)"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_service, require_auth
from app.extended.models import User
from app.services.financial_summary_service import FinancialSummaryService
from app.services.finance_export_service import FinanceExportService
from app.schemas.erp.financial_summary import (
    ProjectSummaryRequest,
    AllProjectsSummaryRequest,
    CompanyOverviewRequest,
    MonthlyTrendRequest,
    BudgetRankingRequest,
    AgingRequest,
    ExportExpensesRequest,
    ExportLedgerRequest,
)
from app.schemas.common import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/project")
async def get_project_summary(
    params: ProjectSummaryRequest,
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
    current_user: User = Depends(require_auth()),
):
    """單一專案財務彙總"""
    result = await service.get_project_summary(params.case_code)
    return SuccessResponse(data=result)


@router.post("/projects")
async def get_all_projects_summary(
    params: AllProjectsSummaryRequest,
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
    current_user: User = Depends(require_auth()),
):
    """所有專案財務一覽"""
    result = await service.get_all_projects_summary(
        year=params.year, skip=params.skip, limit=params.limit
    )
    return SuccessResponse(data=result)


@router.post("/company")
async def get_company_overview(
    params: CompanyOverviewRequest,
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
    current_user: User = Depends(require_auth()),
):
    """全公司財務總覽"""
    result = await service.get_company_overview(
        date_from=params.date_from,
        date_to=params.date_to,
        year=params.year,
        top_n=params.top_n,
    )
    return SuccessResponse(data=result)


@router.post("/monthly-trend")
async def get_monthly_trend(
    params: MonthlyTrendRequest,
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
    current_user: User = Depends(require_auth()),
):
    """月度收支趨勢 — 回溯 N 個月的收入/支出/淨額"""
    result = await service.get_monthly_trend(
        months=params.months,
        case_code=params.case_code,
    )
    return SuccessResponse(data=result)


@router.post("/budget-ranking")
async def get_budget_ranking(
    params: BudgetRankingRequest,
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
    current_user: User = Depends(require_auth()),
):
    """預算使用率排行 — Top N 專案預算消耗"""
    result = await service.get_budget_ranking(
        top_n=params.top_n,
        order_desc=(params.order == "desc"),
    )
    return SuccessResponse(data=result)


@router.post("/aging")
async def get_aging_analysis(
    params: AgingRequest,
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
    current_user: User = Depends(require_auth()),
):
    """應收/應付帳齡分析 — 30/60/90/90+ 天分布"""
    result = await service.get_aging_analysis(
        direction=params.direction,
        year=params.year,
    )
    return SuccessResponse(data=result)


@router.post("/export-expenses")
async def export_expenses(
    params: ExportExpensesRequest,
    service: FinanceExportService = Depends(get_service(FinanceExportService)),
    current_user: User = Depends(require_auth()),
):
    """匯出費用報銷明細 Excel"""
    try:
        xlsx_bytes = await service.export_expenses(
            date_from=params.date_from,
            date_to=params.date_to,
            case_code=params.case_code,
            status=params.status,
        )
    except Exception as e:
        logger.error(f"匯出費用報銷失敗: {e}")
        raise HTTPException(status_code=500, detail="匯出失敗")

    filename = f"expenses_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/erp-overview")
async def get_erp_overview(
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
    current_user: User = Depends(require_auth()),
):
    """ERP 模組快速統計 — Hub 頁面用"""
    from sqlalchemy import select, func
    from app.extended.models.erp import ERPQuotation, ERPInvoice, ERPBilling, ERPVendorPayable
    from app.extended.models.invoice import ExpenseInvoice
    from app.extended.models.finance import FinanceLedger
    from app.extended.models.asset import Asset
    from app.extended.models.operational import OperationalAccount

    db = service.db

    async def count(model):
        return await db.scalar(select(func.count()).select_from(model)) or 0

    async def sum_col(col):
        return await db.scalar(select(func.coalesce(func.sum(col), 0))) or 0

    return SuccessResponse(data={
        "quotations": await count(ERPQuotation),
        "expenses": await count(ExpenseInvoice),
        "ledger": await count(FinanceLedger),
        "invoices": await count(ERPInvoice),
        "assets": await count(Asset),
        "billings": await count(ERPBilling),
        "vendor_payables": await count(ERPVendorPayable),
        "operational": await count(OperationalAccount),
        # Amount summaries
        "quotation_amount": str(await sum_col(ERPQuotation.total_price)),
        "expense_amount": str(await sum_col(ExpenseInvoice.amount)),
        "vendor_payable_amount": str(await sum_col(ERPVendorPayable.payable_amount)),
        "asset_value": str(await sum_col(Asset.current_value)),
    })


@router.post("/export-ledger")
async def export_ledger(
    params: ExportLedgerRequest,
    service: FinanceExportService = Depends(get_service(FinanceExportService)),
    current_user: User = Depends(require_auth()),
):
    """匯出帳本收支明細 Excel"""
    try:
        xlsx_bytes = await service.export_ledger(
            date_from=params.date_from,
            date_to=params.date_to,
            case_code=params.case_code,
            entry_type=params.entry_type,
        )
    except Exception as e:
        logger.error(f"匯出帳本失敗: {e}")
        raise HTTPException(status_code=500, detail="匯出失敗")

    filename = f"ledger_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
