"""ERP 報價 API 端點 (POST-only)"""
import io

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_service, require_auth
from app.extended.models import User
from app.services.erp import ERPQuotationService
from app.schemas.erp.quotation import ERPQuotationDocumentData
from app.schemas.erp import (
    ERPQuotationCreate, ERPQuotationUpdate, ERPQuotationResponse,
    ERPQuotationListRequest,
    ERPIdRequest, ERPQuotationUpdateRequest, ERPQuotationIdRequest,
    ERPQuotationExportRequest,
    ERPQuotationLegacyImportResult,
    ERPSignedImportResult,
    ERPSummaryRequest, ERPGenerateCodeRequest,
    ERPQuotationTemplateMeta,
)
from app.schemas.common import PaginatedResponse, SuccessResponse, DeleteResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# 可跨案查詢報價單的權限 —— owner 2026-08-31：「跨案查報價暫無此考量，
# 但需評估此議題後續彈性擴充機制」。
#
# 做成一個**權限**而不是寫死的角色判斷：日後真的有人要跨案比對單價、
# 找歷史案例時，**授予這個權限即可，不必改程式碼**。
# 目前無人持有 ⇒ 行為等同「只有管理者看得到全部」。
QUOTATION_CROSS_CASE_PERMISSION = "reports:erp:view"


def _quotation_scope(user):
    """回可見的 case_code 範圍；**None ＝ 不限縮**。

    ⚠️ 範圍由**伺服器依身分**決定，不接受請求參數指定 ——
    否則前端傳什麼就給什麼，等於沒有 RLS。
    """
    from app.core.auth_service import AuthService
    from app.core.dependencies import is_admin_user, is_superuser_user
    from app.core.rls_filter import RLSFilter

    # 管理員判定走既有 SSOT（併看 flag 與 role）—— 本 repo 有兩位 role=admin
    # 而 is_admin 旗標為 false，只看旗標會把他們當成一般同仁。
    if is_superuser_user(user) or is_admin_user(user):
        return None
    if AuthService.check_permission(user, QUOTATION_CROSS_CASE_PERMISSION):
        return None
    return RLSFilter.get_user_accessible_case_codes(user.id)


@router.post("/list")
async def list_quotations(
    params: ERPQuotationListRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
    current_user: User = Depends(require_auth()),
):
    """報價列表。

    ⭐ 2026-08-31 兩層收斂（owner）：
      · **成案主軸** —— 預設只給有承攬案件的報價單（`include_unawarded` 可取回）
      · **依身分限縮** —— 一般同仁只看自己被指派的案子，與 /contract-cases 同一條規則
    """
    scope = _quotation_scope(current_user)
    items, total = await service.list_quotations(params, accessible_case_codes=scope)
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
    try:
        result = await service.update(req.id, req.data)
    except ValueError as e:
        # 2026-09-03：服務層的業務拒絕（例如有請款後改總價）要變 400 說清楚，不是 500
        raise HTTPException(status_code=400, detail=str(e))
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
    result = await service.get_profit_summary(year=req.year, search=req.search)
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
    """匯入報價 Excel（總表格式）。

    2026-09-03：此端點原本吃另一套 11 欄範本，與匯出／總表對不上，且會建出沒有編號的報價單。
    改為與 `/import-legacy` 同一條路（dry_run=False），回傳維持 {total_rows, created, updated, errors}
    讓既有呼叫端不壞。前端已改用 import-legacy 的「先預覽再確認」流程。
    """
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 .xlsx/.xls 格式")
    content = await file.read()
    from app.services.erp.quotation_legacy_import import QuotationLegacyImportService
    r = await QuotationLegacyImportService(service.db).run(content, dry_run=False, user_id=current_user.id)
    if not r.get("success", True):
        raise HTTPException(status_code=400, detail=r.get("error", "匯入失敗"))
    return SuccessResponse(data={
        "total_rows": r.get("total_rows", 0), "created": r.get("created", 0), "updated": r.get("updated", 0),
        "errors": [], "finance": r.get("finance"), "skipped": r.get("skipped", 0),
    })


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


@router.post("/import-signed", response_model=SuccessResponse[ERPSignedImportResult])
async def import_signed_quotations(
    files: list[UploadFile] = File(...),
    dry_run: bool = True,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
    current_user: User = Depends(require_auth()),
):
    """匯入客戶回簽報價單（依檔名的舊案號自動掛回對應案件）。

    owner 2026-08-19：「產生報價單只是步驟一，其需將客戶回簽檔案上傳確認
    才正式完成邀標報價承攬」。

    檔名格式：`回簽報價單_<舊案號>_<客戶>_<標的>_<項目>.pdf`

    ⚠️ 比對走**正規化**：回簽檔寫 `B115-C017a-0`、彙整表寫 `B115-C017-a`，
    直接字串比對 5 個檔會有 3 個掛不上（2026-08-19 實測）。

    `dry_run=True`（預設）只回報「幾個對得上、幾個對不上」不寫入；
    對不上的會列出檔名與原因，不靜靜跳過。
    """
    from app.services.erp.signed_quotation_import import SignedQuotationImportService

    payload: list[tuple[str, bytes]] = []
    for f in files:
        if not f.filename:
            continue
        payload.append((f.filename, await f.read()))
    if not payload:
        raise HTTPException(status_code=400, detail="沒有可處理的檔案")

    svc = SignedQuotationImportService(service.db)
    return SuccessResponse(data=await svc.run(
        payload, dry_run=dry_run, user_id=current_user.id,
    ))


@router.post("/import-legacy", response_model=SuccessResponse[ERPQuotationLegacyImportResult])
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
        r = await svc.run(content, dry_run=dry_run, user_id=current_user.id, source_name=file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 2026-09-03：檔案沒有「報價單編號」欄（上傳到錯的檔）時 importer 回 {success: False, error}，
    # 而 response_model 要成功形狀 ⇒ 原本 500。錯的檔是使用者的錯，回 400 說清楚。
    if r.get("success") is False:
        raise HTTPException(status_code=400, detail=r.get("error") or "匯入失敗")
    return SuccessResponse(data=r)


@router.post("/template-preview")
async def quotation_template_preview(
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
    current_user: User = Depends(require_auth()),
):
    """報價單 XLS 範本樣式預覽 —— 空白範本轉 PDF（owner 2026-08-29
    「xls樣本報價單無法呈現嗎」）。

    版面唯一來源＝`app/templates/quotation_template.xlsx`；這裡**不填值**，
    使用者看到的正是輸出時的版面（同一條 LibreOffice 轉換鏈）。
    與「輸出 PDF」的差別：那個要先有報價單，這個在建單前就能看。
    """
    from pathlib import Path as _Path

    from app.services.erp import quotation_document as _qd
    from app.services.erp.quotation_document import QuotationDocumentService

    # 與 render_xlsx 內部同一條路徑推導（quotation_document.py:321）
    tpl = _Path(_qd.__file__).resolve().parents[2] / "templates" / "quotation_template.xlsx"
    if not tpl.exists():
        raise HTTPException(status_code=500, detail=f"範本不存在：{tpl.name}")
    try:
        # 2026-09-04 owner「檢視 XLS 樣式格式錯誤」：此前把範本檔**原樣**轉 PDF ——
        # 而範本檔不是空白的（owner 給的實際報價單：客戶、承辦 email、金額都在裡面），
        # 也沒有 fitToPage ⇒ 預覽是 4 頁、印著別人的報價。正式輸出走 render_xlsx 清值＋縮放，
        # 預覽也走同一條：空資料填進去，使用者看到的才是「輸出時的版面」。
        blank = {"display_no": "", "items": [], "category": "", "has_items": False}
        pdf = QuotationDocumentService.render_pdf(QuotationDocumentService(None).render_xlsx(blank))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"PDF 轉換失敗：{e}")
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="quotation_template_preview.pdf"'},
    )


@router.post("/template-meta", response_model=SuccessResponse[ERPQuotationTemplateMeta])
async def quotation_template_meta(
    current_user: User = Depends(require_auth()),
):
    """正式 XLS 範本的容量 —— 前端唯一容量來源。

    2026-08-29：明細上限 5 → 10 時，前端有一份手抄的 `TEMPLATE_ITEM_CAPACITY = 5`
    沒跟著改，第 6 項起會警告使用者「需先合併」—— 叫人去手動合併後端其實
    輸出得出來的工項。**tsc 檢查不出一個過期的字面值**，只有把數字搬回
    單一來源才擋得住下一次。

    值由 `ITEM_FIRST_ROW/ITEM_LAST_ROW` 推導，不另外寫一個常數
    （另寫一個就是第三份 SSOT）。
    """
    from app.services.erp.quotation_document import QuotationDocumentService as _Q

    return SuccessResponse(data=ERPQuotationTemplateMeta(
        item_capacity=_Q.ITEM_LAST_ROW - _Q.ITEM_FIRST_ROW + 1,
        notes_row=_Q.NOTES_ROW,
    ))


@router.post("/document-data", response_model=SuccessResponse[ERPQuotationDocumentData])
async def quotation_document_data(
    req: ERPQuotationIdRequest,
    service: ERPQuotationService = Depends(get_service(ERPQuotationService)),
    current_user: User = Depends(require_auth()),
):
    """正式文件會印出來的抬頭資料（客戶／聯絡人／工作地點／服務人員）與各自的來源 id。

    2026-09-04 owner「報價單無法編輯客戶資訊」：這些欄位不存在報價單上，來自委託單位主檔、PM 案、承辦指派。
    這個端點把「文件上會印什麼」原樣回給前端，並附來源 id 讓頁面給出編輯入口——不在報價單上另存一份。
    """
    from app.services.erp.quotation_document import QuotationDocumentService
    try:
        data = await QuotationDocumentService(service.db).gather(req.erp_quotation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    data.pop("items", None)
    if data.get("quoted_date") is not None:
        data["quoted_date"] = str(data["quoted_date"])
    for k in ("items_subtotal", "tax_amount", "total_price"):
        if data.get(k) is not None:
            data[k] = float(data[k])
    return SuccessResponse(data=ERPQuotationDocumentData.model_validate(data))


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
        # 2026-08-28 owner 更新（取代 08-19「標案不輸出」）：「委辦案件無仍呈現
        # 報價單」—— 01 也開放輸出。renderer 會在文件上自動加註
        # 「本案為委辦招標案，依招標文件所列項目辦理」（quotation_document.py）。
        # 前端同日已放開按鈕；這裡若仍擋 400 就是前後端各說各話的半接通。
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
    # 2026-08-28：存檔結果讓前端看得到（X-Archive-Status header）。
    # 先前只寫 log —— 而 UI 對使用者承諾「輸出後自動存入本案附件」，
    # 沒存成時使用者無從得知（出聲只到 log 層等於沒出到人面前）。
    archive_status = "skipped"
    if request.archive:
        try:
            await doc.archive(data, content, ext, current_user.id)
            archive_status = "ok"
        except Exception as e:
            # 存檔失敗**不擋下載**（使用者手上這份仍是好的），
            # 但一定要出聲：靜靜地沒存進系統，正是最不會被發現的那種失敗。
            archive_status = "failed"
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
        headers={
            "Content-Disposition": disposition,
            "X-Archive-Status": archive_status,
            # 自訂 header 需列入 expose 否則跨域 JS 讀不到（CORS 預設只給 simple headers）
            "Access-Control-Expose-Headers": "X-Archive-Status",
        },
    )
