"""ERP 報價 API 端點 (POST-only)"""
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_service
from app.services.erp import ERPQuotationService
from app.schemas.erp import (
    ERPQuotationCreate, ERPQuotationUpdate, ERPQuotationResponse,
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


@router.post(
    "/detail",
    # 2026-08-17：補上 OpenAPI 契約。
    #
    # 這一檔 14 個端點原本**都沒有宣告 response_model**（回 SuccessResponse 包裝），
    # 於是 `ERPQuotationResponse` **從來不在 OpenAPI 裡** ——
    # 而前端 `types/erp.ts` 的依據正是那份契約。
    # 結果是後端加了欄位（quotation_no/revision），契約完全看不出來，
    # 前端只能靠人去讀後端程式碼才知道有這些欄位。
    #
    # ⚠️ 刻意**只補這一個端點**，不改另外 13 個：
    # 那會一次動到整份契約（OpenAPI 快照測試會全紅），
    # 而收益是「文件更完整」—— 與風險不成比例。
    # `responses` 而非 `response_model`：後者會讓 FastAPI 真的去驗證並過濾回應，
    # 而這裡實際回的是 `SuccessResponse(data=dict)` 帶額外的 pm_contract_amount，
    # 用 response_model 會把那兩個欄位**濾掉**（又一次靜默丟棄）。
    responses={200: {"model": ERPQuotationResponse,
                     "description": "報價詳情（實際包在 SuccessResponse.data，"
                                    "另含 pm_contract_amount / amount_mismatch）"}},
)
async def get_quotation_detail(
    req: ERPIdRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """報價詳情 (含損益計算 + PM 金額比對)"""
    result = await service.get_detail(req.id)
    if not result:
        raise HTTPException(status_code=404, detail="報價不存在")

    # PM 金額比對 — 附加 pm_contract_amount 和差異標記
    data = result.model_dump() if hasattr(result, 'model_dump') else result
    pm_info = await service.get_pm_amount_check(result.case_code)
    if pm_info:
        data["pm_contract_amount"] = pm_info["pm_contract_amount"]
        data["amount_mismatch"] = pm_info["mismatch"]
    return SuccessResponse(data=data)


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


@router.post("/export-excel")
async def export_quotations_excel(
    req: ERPSummaryRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """匯出報價 Excel (.xlsx，含損益)"""
    content = await service.export_excel(year=req.year)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=erp_quotations.xlsx"},
    )


@router.post("/import-template")
async def download_import_template(
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """下載報價匯入範本 Excel"""
    content = service.generate_import_template()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=erp_quotation_template.xlsx"},
    )


@router.post("/import")
async def import_quotations(
    file: UploadFile = File(...),
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
):
    """匯入報價 Excel (.xlsx/.xls)"""
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 .xlsx/.xls 格式")
    content = await file.read()
    result = await service.import_from_excel(content)
    return SuccessResponse(data=result)


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
