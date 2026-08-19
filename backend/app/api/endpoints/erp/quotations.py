"""ERP 報價 API 端點 (POST-only)"""
import io

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_service, require_auth
from app.extended.models import User
from app.services.erp import ERPQuotationService
from app.schemas.erp import (
    ERPQuotationCreate, ERPQuotationUpdate, ERPQuotationResponse,
    ERPQuotationListRequest,
    ERPIdRequest, ERPQuotationUpdateRequest, ERPQuotationIdRequest,
    ERPQuotationExportRequest,
    ERPSummaryRequest, ERPGenerateCodeRequest,
)
from app.schemas.common import PaginatedResponse, SuccessResponse, DeleteResponse

logger = logging.getLogger(__name__)

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
    current_user: User = Depends(require_auth()),
):
    """建立報價。

    ⚠️ `user_id` 一定要傳：`service.create` 早就用它寫 `created_by`，
    但這裡原本沒傳 —— 於是 **77 張報價單的 `created_by` 全部是 NULL**
    （2026-08-18 實測），而正式報價單的「服務人員／E-mail」正是取自它。
    欄位存在、service 支援、端點不傳 = 半接通，沒有任何一層會報錯。
    """
    result = await service.create(data, user_id=current_user.id)
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
        # 2026-08-17：改用 .get —— `get_pm_amount_check` 現在可能只回
        # client_name（沒填 PM 金額的案件），直接 [] 取值會 KeyError。
        if "pm_contract_amount" in pm_info:
            data["pm_contract_amount"] = pm_info["pm_contract_amount"]
            data["amount_mismatch"] = pm_info.get("mismatch")
        if pm_info.get("client_name"):
            data["client_name"] = pm_info["client_name"]
        if pm_info.get("case_category"):
            data["case_category"] = pm_info["case_category"]
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
    current_user: User = Depends(require_auth()),
):
    """匯入報價 Excel (.xlsx/.xls)"""
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 .xlsx/.xls 格式")
    content = await file.read()
    # 與單筆建立同理：匯入進來的報價一樣要記得是誰匯的（見 create_quotation）
    result = await service.import_from_excel(content, user_id=current_user.id)
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


@router.post("/import-legacy")
async def import_legacy_quotations(
    file: UploadFile = File(...),
    dry_run: bool = True,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
    current_user: User = Depends(require_auth()),
):
    """匯入既有報價單彙整 XLS（個人管理時期的資料）。

    owner 2026-08-19：「若線上產出報價單未完全上線前，如何匯入與管理既有 XLS
    為目前階段重點」「新增與更新整合為一個按鍵鈕」。

    **一個入口做 upsert**：依舊案號（`B114-B002`）比對，有就更新、沒有就新增。
    使用者不需要先知道 277 列裡哪些已在系統 —— 他也無從知道。

    `dry_run=True`（預設）只回報「會新增幾筆、更新幾筆」不寫入。
    第一次匯入 277 筆業務資料，沒有預覽就寫進去，錯了要靠備份還原。
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="僅支援 .xlsx/.xls 格式")
    # .xls 是 BIFF，openpyxl 讀不了 —— 明講而不是丟一個看不懂的解析錯誤
    if file.filename.lower().endswith(".xls"):
        raise HTTPException(
            status_code=400,
            detail="這是舊版 .xls（BIFF）格式，請先用 Excel 另存為 .xlsx 再匯入",
        )

    from app.services.erp.quotation_legacy_import import QuotationLegacyImportService

    content = await file.read()
    svc = QuotationLegacyImportService(service.db)
    try:
        return SuccessResponse(data=await svc.run(
            content, dry_run=dry_run, user_id=current_user.id,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/export-document")
async def export_quotation_document(
    request: ERPQuotationExportRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
    current_user: User = Depends(require_auth()),
):
    """輸出報價單正式文件（xlsx／pdf），並自動存進系統。

    owner 2026-08-17：「新增報價單要可輸出正式文件，非僅資料列表用途」
    owner 2026-08-18：「報價單要能輸出 pdf 並且自動納入系統存檔」

    以 `app/templates/quotation_template.xlsx` 為底填值 —— 該範本取自
    owner 提供的實際報價單，內含公司抬頭圖片、框線、合計公式與簽章欄。
    **換版面是換那個檔，不是改這裡**；PDF 也是從同一份 xlsx 轉出，
    所以版面永遠只有一份來源。
    """
    from urllib.parse import quote

    from app.services.erp.quotation_document import QuotationDocumentService

    doc = QuotationDocumentService(service.db)
    try:
        data = await doc.gather(request.erp_quotation_id)
        content = doc.render_xlsx(data)
        if request.format == "pdf":
            content = doc.render_pdf(content)
    except ValueError as e:
        # 找不到報價、或明細超過範本列數 —— 兩者都要讓使用者看到原因，
        # 而不是一個沒有訊息的 500。
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        # PDF 轉換失敗（缺 LibreOffice／soffice 卡住／產物不是 PDF）。
        # 不退回 xlsx 假裝成功 —— 那會讓使用者拿到副檔名 .pdf 卻打不開的檔案。
        raise HTTPException(status_code=500, detail=f"PDF 轉換失敗：{e}")

    ext = request.format
    if request.archive:
        try:
            await doc.archive(data, content, ext, current_user.id)
        except Exception as e:
            # 存檔失敗**不擋下載**（使用者手上這份仍是好的），
            # 但一定要出聲：靜靜地沒存進系統，正是最不會被發現的那種失敗。
            logger.error("報價單存檔失敗 qid=%s: %s", request.erp_quotation_id, e, exc_info=True)

    filename = doc.suggest_filename(data)
    if ext == "pdf":
        filename = filename.rsplit(".", 1)[0] + ".pdf"
    # ⚠️ 檔名含中文（案名），必須用 RFC 5987 `filename*=UTF-8''…`。
    # 既有匯出端點全是 ASCII 檔名所以沒踩到這件事；
    # 只給 `filename=` 的話瀏覽器會存成亂碼或直接截斷。
    # 同時保留一個 ASCII 後備給不支援 RFC 5987 的舊客戶端。
    ascii_fallback = f"quotation_{data['quotation_no'] or data['quotation_id']}.{ext}"
    disposition = (
        f"attachment; filename=\"{ascii_fallback}\"; "
        f"filename*=UTF-8''{quote(filename)}"
    )
    return StreamingResponse(
        iter([content]),
        media_type=(
            "application/pdf" if ext == "pdf"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": disposition},
    )
