"""PM 案件 API 端點 (POST-only)"""
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_service
from app.services.pm import PMCaseService
from app.schemas.pm import (
    PMCaseCreate, PMCaseUpdate, PMCaseResponse,
    PMCaseListRequest, PMCaseSummary,
    PMCaseIdRequest, PMCaseUpdateRequest,
    PMSummaryRequest, PMGenerateCodeRequest,
    PMCrossLookupRequest, PMLinkedDocsRequest, PMPromoteRequest,
)
from app.schemas.common import PaginatedResponse, SuccessResponse, DeleteResponse

router = APIRouter()


@router.post("/list")
async def list_cases(
    params: PMCaseListRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """案件列表"""
    items, total = await service.list_cases(params)
    return PaginatedResponse.create(items=items, total=total, page=params.page, limit=params.limit)


@router.post("/create")
async def create_case(
    data: PMCaseCreate,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """建立案件"""
    result = await service.create(data)
    return SuccessResponse(data=result, message="案件建立成功")


@router.post("/yearly-trend")
async def get_yearly_trend(
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """多年度案件趨勢"""
    result = await service.get_yearly_trend()
    return SuccessResponse(data=result)


@router.post("/detail")
async def get_case_detail(
    req: PMCaseIdRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """案件詳情"""
    result = await service.get_detail(req.id)
    if not result:
        raise HTTPException(status_code=404, detail="案件不存在")
    return SuccessResponse(data=result)


@router.post("/update")
async def update_case(
    data: PMCaseUpdate,
    case_id: int = 0,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """更新案件 (case_id 由 request body 的 id 欄位或查詢參數傳入)"""
    result = await service.update(case_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="案件不存在")
    return SuccessResponse(data=result, message="案件更新成功")


@router.post("/update-by-id")
async def update_case_by_id(
    req: PMCaseUpdateRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """更新案件 (POST body 包含 id + data)"""
    result = await service.update(req.id, req.data)
    if not result:
        raise HTTPException(status_code=404, detail="案件不存在")
    return SuccessResponse(data=result, message="案件更新成功")


@router.post("/delete")
async def delete_case(
    req: PMCaseIdRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """刪除案件"""
    success = await service.delete(req.id)
    if not success:
        raise HTTPException(status_code=404, detail="案件不存在")
    return DeleteResponse(deleted_id=req.id)


@router.post("/summary")
async def get_summary(
    req: PMSummaryRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """案件統計摘要"""
    result = await service.get_summary(year=req.year)
    return SuccessResponse(data=result)


@router.post("/generate-code")
async def generate_case_code(
    req: PMGenerateCodeRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """產生 PM 案號"""
    code = await service.generate_case_code(year=req.year, category=req.category)
    return SuccessResponse(data={"case_code": code})


@router.post("/recalculate-progress")
async def recalculate_progress(
    req: PMCaseIdRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """根據里程碑完成率重新計算進度"""
    progress = await service.recalculate_progress(req.id)
    if progress is None:
        raise HTTPException(status_code=404, detail="案件不存在或無里程碑")
    return SuccessResponse(data={"progress": progress})


@router.post("/gantt")
async def generate_gantt(
    req: PMCaseIdRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """產生案件里程碑甘特圖 (Mermaid Gantt 語法)"""
    gantt = await service.generate_gantt(req.id)
    if gantt is None:
        raise HTTPException(status_code=404, detail="案件不存在")
    return SuccessResponse(data={"gantt_mermaid": gantt})


@router.post("/export")
async def export_cases(
    req: PMSummaryRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """匯出案件 CSV"""
    csv_content = await service.export_csv(year=req.year)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pm_cases.csv"},
    )


@router.post("/cross-lookup")
async def cross_module_lookup(
    req: PMCrossLookupRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """跨模組案號查詢 — 回傳 PM/ERP 兩端資料"""
    result = await service.code_service.cross_module_lookup(req.case_code)
    return SuccessResponse(data=result)


@router.post("/linked-documents")
async def get_linked_documents(
    req: PMLinkedDocsRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """透過案號查詢相關公文 (case_code → ContractProject → OfficialDocument)"""
    docs = await service.code_service.find_linked_documents(req.case_code, req.limit)
    return SuccessResponse(data=docs)


@router.post("/promote")
async def promote_to_project(
    req: PMPromoteRequest,
    service: PMCaseService = Depends(get_service(PMCaseService)),
):
    """成案：從邀標/報價轉為正式承攬案件

    自動產生 project_code，建立 ContractProject，連結 ERP Quotation。
    """
    try:
        result = await service.code_service.promote_to_project(req.case_code)
        return SuccessResponse(data=result, message=f"成案成功，專案編號: {result['project_code']}")
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
