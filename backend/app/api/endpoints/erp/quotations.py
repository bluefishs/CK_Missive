"""ERP 報價 API 端點 (POST-only)"""
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_service
from app.services.erp import ERPQuotationService
from app.schemas.erp import (
    ERPQuotationCreate, ERPQuotationUpdate,
    ERPQuotationListRequest,
    ERPIdRequest, ERPQuotationUpdateRequest,
    ERPSummaryRequest, ERPGenerateCodeRequest,
)
from app.schemas.common import PaginatedResponse, SuccessResponse, DeleteResponse

router = APIRouter()


@router.post("/list")
async def list_quotations(
    params: ERPQuotationListRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """報價列表"""
    items, total = await service.list_quotations(params)
    return PaginatedResponse.create(items=items, total=total, page=params.page, limit=params.limit)


@router.post("/create")
async def create_quotation(
    data: ERPQuotationCreate,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """建立報價"""
    result = await service.create(data)
    return SuccessResponse(data=result, message="報價建立成功")


@router.post("/detail")
async def get_quotation_detail(
    req: ERPIdRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """報價詳情 (含損益計算)"""
    result = await service.get_detail(req.id)
    if not result:
        raise HTTPException(status_code=404, detail="報價不存在")
    return SuccessResponse(data=result)


@router.post("/update")
async def update_quotation(
    req: ERPQuotationUpdateRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """更新報價"""
    result = await service.update(req.id, req.data)
    if not result:
        raise HTTPException(status_code=404, detail="報價不存在")
    return SuccessResponse(data=result, message="報價更新成功")


@router.post("/delete")
async def delete_quotation(
    req: ERPIdRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """刪除報價"""
    success = await service.delete(req.id)
    if not success:
        raise HTTPException(status_code=404, detail="報價不存在")
    return DeleteResponse(deleted_id=req.id)


@router.post("/profit-summary")
async def get_profit_summary(
    req: ERPSummaryRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """損益摘要"""
    result = await service.get_profit_summary(year=req.year)
    return SuccessResponse(data=result)


@router.post("/profit-trend")
async def get_profit_trend(
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """多年度損益趨勢 — 各年度收入/成本/毛利/毛利率/案件數"""
    result = await service.get_profit_trend()
    return SuccessResponse(data=result)


@router.post("/export")
async def export_quotations(
    req: ERPSummaryRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """匯出報價 CSV (含損益)"""
    csv_content = await service.export_csv(year=req.year)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=erp_quotations.csv"},
    )


@router.post("/case-code-map")
async def get_case_code_map(
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """案號→成案編號對照表"""
    from sqlalchemy import select as sa_select
    from app.extended.models.erp import ERPQuotation
    result = await service.db.execute(
        sa_select(ERPQuotation.case_code, ERPQuotation.project_code)
        .where(ERPQuotation.project_code.isnot(None))
    )
    mapping = {r[0]: r[1] for r in result.all()}
    return SuccessResponse(data=mapping)


@router.post("/generate-code")
async def generate_case_code(
    req: ERPGenerateCodeRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """產生 ERP 案號"""
    code = await service.generate_case_code(year=req.year, category=req.category)
    return SuccessResponse(data={"case_code": code})
