"""跨模組財務彙總 API 端點 (POST-only)"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_service
from app.services.financial_summary_service import FinancialSummaryService
from app.schemas.erp.financial_summary import (
    ProjectSummaryRequest,
    AllProjectsSummaryRequest,
    CompanyOverviewRequest,
)
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.post("/project")
async def get_project_summary(
    params: ProjectSummaryRequest,
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
):
    """單一專案財務彙總"""
    result = await service.get_project_summary(params.case_code)
    return SuccessResponse(data=result)


@router.post("/projects")
async def get_all_projects_summary(
    params: AllProjectsSummaryRequest,
    service: FinancialSummaryService = Depends(get_service(FinancialSummaryService)),
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
):
    """全公司財務總覽"""
    result = await service.get_company_overview(
        date_from=params.date_from,
        date_to=params.date_to,
        year=params.year,
        top_n=params.top_n,
    )
    return SuccessResponse(data=result)
