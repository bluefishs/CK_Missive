"""費用報銷發票 API 端點 (POST-only)"""
import os
import uuid
import logging
from decimal import Decimal
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse

from app.core.dependencies import get_service, optional_auth, require_auth, require_permission
from app.extended.models import User
from app.services.expense_invoice_service import ExpenseInvoiceService
from app.schemas.erp.expense import (
    ExpenseInvoiceCreate,
    ExpenseInvoiceQuery,
    ExpenseInvoiceResponse,
    ExpenseInvoiceUpdateRequest,
    ExpenseInvoiceRejectRequest,
    ExpenseInvoiceQRScanRequest,
)
from app.schemas.erp.requests import ERPIdRequest
from app.schemas.common import PaginatedResponse, SuccessResponse

logger = logging.getLogger(__name__)

# 收據影像儲存目錄 (與 einvoice_sync 共用)
RECEIPT_UPLOAD_DIR = Path(os.getenv("RECEIPT_UPLOAD_DIR", "uploads/receipts"))
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
MAX_RECEIPT_SIZE = 10 * 1024 * 1024  # 10MB

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
    """費用核銷按歸屬分組彙總 — 專案/營運/未歸屬各自統計

    回傳結構參照 vendor-accounts 模式：
    groups: [
      { group_key, group_label, attribution_type, case_code, total_amount, count, items: [...] }
    ]
    """
    body = await request.json()
    attribution_type = body.get("attribution_type")

    from sqlalchemy import select, func, case as sa_case
    from app.extended.models.invoice import ExpenseInvoice

    # 分組查詢
    stmt = (
        select(
            ExpenseInvoice.attribution_type,
            ExpenseInvoice.case_code,
            ExpenseInvoice.category,
            func.count(ExpenseInvoice.id).label("count"),
            func.sum(ExpenseInvoice.amount).label("total_amount"),
        )
        .group_by(ExpenseInvoice.attribution_type, ExpenseInvoice.case_code, ExpenseInvoice.category)
        .order_by(func.sum(ExpenseInvoice.amount).desc())
    )

    if attribution_type:
        stmt = stmt.where(ExpenseInvoice.attribution_type == attribution_type)

    result = await service.db.execute(stmt)
    rows = result.all()

    # 組合為 group 結構
    group_map: dict = {}
    for row in rows:
        attr = row.attribution_type or "none"
        cc = row.case_code or "__operational__" if attr == "operational" else (row.case_code or "__none__")
        key = f"{attr}:{cc}"

        if key not in group_map:
            if attr == "project" and cc:
                label = cc
            elif attr == "operational":
                label = "營運費用"
            else:
                label = "未歸屬"
            group_map[key] = {
                "group_key": key,
                "group_label": label,
                "attribution_type": attr,
                "case_code": row.case_code,
                "total_amount": 0,
                "count": 0,
                "categories": [],
            }
        g = group_map[key]
        g["total_amount"] += float(row.total_amount or 0)
        g["count"] += row.count
        if row.category:
            g["categories"].append({
                "category": row.category,
                "count": row.count,
                "amount": float(row.total_amount or 0),
            })

    # 查 case_code → project_code 映射補標簽
    from app.extended.models.erp import ERPQuotation
    if any(g["case_code"] for g in group_map.values()):
        codes = [g["case_code"] for g in group_map.values() if g["case_code"]]
        q = await service.db.execute(
            select(ERPQuotation.case_code, ERPQuotation.project_code, ERPQuotation.case_name)
            .where(ERPQuotation.case_code.in_(codes))
        )
        code_info = {r.case_code: r for r in q.all()}
        for g in group_map.values():
            if g["case_code"] and g["case_code"] in code_info:
                info = code_info[g["case_code"]]
                g["group_label"] = f"{info.project_code or info.case_code} {info.case_name or ''}"
                g["project_code"] = info.project_code

    groups = sorted(group_map.values(), key=lambda x: x["total_amount"], reverse=True)
    total = sum(g["total_amount"] for g in groups)

    return SuccessResponse(data={
        "groups": groups,
        "total_count": sum(g["count"] for g in groups),
        "total_amount": total,
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
        return SuccessResponse(data=result, message="報銷發票建立成功")
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
    return SuccessResponse(data=result)


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
    return SuccessResponse(data=result, message="更新成功")


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

    權限需求: projects:write (主管/財務)
    禁止自我審核: 申請人不可審核自己的報銷
    """
    # 禁止自我審核
    invoice = await service.get_by_id(params.id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")
    if invoice.user_id and invoice.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="不可審核自己提交的報銷")

    try:
        result = await service.approve(params.id)
        if not result:
            raise HTTPException(status_code=404, detail="發票不存在")
        status_msg = {
            "manager_approved": "主管已核准，等待下一層審核",
            "finance_approved": "財務已核准，等待最終確認",
            "verified": "審核通過，已自動入帳",
        }
        msg = status_msg.get(result.status, "審核推進成功")
        # 附加預算警告 (若有)
        budget_warning = getattr(result, "_budget_warning", None)
        if budget_warning:
            msg = f"{msg}。{budget_warning}"
        return SuccessResponse(data=result, message=msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reject")
async def reject_expense(
    params: ExpenseInvoiceRejectRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_permission("projects:write")),
):
    """駁回報銷 (權限需求: projects:write)"""
    try:
        result = await service.reject(params.id, reason=params.reason)
        if not result:
            raise HTTPException(status_code=404, detail="發票不存在")
        return SuccessResponse(data=result, message="已駁回")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/qr-scan")
async def create_from_qr(
    params: ExpenseInvoiceQRScanRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(optional_auth()),
):
    """QR Code 掃描建立報銷發票"""
    try:
        user_id = current_user.id if current_user else None
        result = await service.create_from_qr(
            raw_qr=params.raw_qr,
            case_code=params.case_code,
            category=params.category,
            user_id=user_id,
        )
        return SuccessResponse(data=result, message="QR 發票建立成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auto-link-einvoice")
async def auto_link_einvoice(
    req: ERPIdRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """自動關聯電子發票 — 用 inv_num 匹配電子發票同步批次"""
    result = await service.auto_link_einvoice(req.id)
    if not result:
        raise HTTPException(status_code=404, detail="發票不存在或缺少發票號碼")
    return SuccessResponse(data=result)


@router.post("/upload-receipt")
async def upload_expense_receipt(
    invoice_id: int = Form(..., description="發票 ID"),
    file: UploadFile = File(..., description="收據影像"),
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """上傳收據影像至費用發票 (不變更狀態，僅附加圖片)"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的檔案格式: {file.content_type}，請上傳 JPEG/PNG/WebP/HEIC",
        )

    content = await file.read()
    if len(content) > MAX_RECEIPT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"檔案過大 ({len(content) // 1024 // 1024}MB)，上限為 10MB",
        )

    RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "receipt.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = RECEIPT_UPLOAD_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    relative_path = f"receipts/{filename}"
    try:
        result = await service.attach_receipt(invoice_id, relative_path)
    except ValueError as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail="發票不存在")

    return SuccessResponse(data=result, message="收據上傳成功")


@router.post("/ocr-parse")
async def ocr_parse_invoice(
    file: UploadFile = File(..., description="發票影像"),
    current_user: User = Depends(require_auth()),
):
    """OCR 辨識發票影像，回傳結構化資訊供前端自動填入表單

    支援 JPEG/PNG/WebP/HEIC 格式，上限 10MB。
    辨識結果含信心度 (0~1)，使用者可修正後送出。
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的檔案格式: {file.content_type}，請上傳 JPEG/PNG/WebP/HEIC",
        )

    content = await file.read()
    if len(content) > MAX_RECEIPT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"檔案過大 ({len(content) // 1024 // 1024}MB)，上限為 10MB",
        )

    # 儲存暫存影像供 OCR 處理
    RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "invoice.jpg").suffix or ".jpg"
    filename = f"ocr_{uuid.uuid4().hex}{ext}"
    file_path = RECEIPT_UPLOAD_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # OCR 辨識
    from app.services.invoice_ocr_service import InvoiceOCRService
    ocr_service = InvoiceOCRService()
    try:
        result = ocr_service.parse_image(str(file_path))
    except Exception as e:
        logger.error(f"OCR 辨識失敗: {e}")
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="OCR 辨識過程發生錯誤")

    # 保留影像供後續建立發票時引用
    relative_path = f"receipts/{filename}"
    result_dict = result.model_dump()
    result_dict["source_image_path"] = relative_path

    return SuccessResponse(data=result_dict, message="OCR 辨識完成")


@router.post("/smart-scan")
async def smart_scan_invoice(
    file: UploadFile = File(..., description="發票影像（支援 QR 或紙本）"),
    case_code: str = Form(None, description="成案編號 (選填)"),
    category: str = Form(None, description="費用分類 (選填)"),
    auto_create: bool = Form(True, description="辨識成功是否自動建立記錄"),
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(optional_auth()),
):
    """智慧發票辨識 — QR 優先 + OCR 補充，一張照片搞定

    流程：
    1. 上傳發票照片（手機拍照 / 掃描文件 / LINE 轉傳）
    2. 系統自動偵測 QR Code，失敗則執行 OCR
    3. 辨識成功且 auto_create=true 時自動建立費用記錄
    4. 回傳辨識結果供前端預覽/修正
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="僅支援 JPEG/PNG/WebP/HEIC 格式")

    content = await file.read()
    if len(content) > MAX_RECEIPT_SIZE:
        raise HTTPException(status_code=400, detail="檔案過大，上限 10MB")

    # 儲存影像
    RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "scan.jpg").suffix or ".jpg"
    filename = f"scan_{uuid.uuid4().hex[:8]}{ext}"
    file_path = RECEIPT_UPLOAD_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # 統一辨識
    from app.services.invoice_recognizer import recognize_invoice
    recognition = recognize_invoice(str(file_path))

    result_data = recognition.to_dict()
    result_data["receipt_path"] = f"uploads/receipts/{filename}"

    # 自動建立記錄
    if recognition.success and auto_create:
        try:
            from app.schemas.erp.expense import ExpenseInvoiceCreate
            user_id = current_user.id if current_user else None
            create_data = ExpenseInvoiceCreate(
                inv_num=recognition.inv_num,
                date=recognition.date,
                amount=recognition.amount or Decimal("0"),
                tax_amount=recognition.tax_amount,
                buyer_ban=recognition.buyer_ban,
                seller_ban=recognition.seller_ban,
                case_code=case_code,
                category=category,
                source=f"smart_{recognition.method}",
            )
            invoice = await service.create(
                create_data, user_id=user_id,
                receipt_image_path=f"uploads/receipts/{filename}",
            )
            result_data["created"] = True
            result_data["invoice_id"] = invoice.id if hasattr(invoice, 'id') else invoice.get('id')
            result_data["message"] = f"發票 {recognition.inv_num} 已自動建立"
        except ValueError as e:
            result_data["created"] = False
            result_data["message"] = str(e)
    else:
        result_data["created"] = False

    return SuccessResponse(data=result_data)


@router.post("/import-template")
async def download_expense_template(
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
):
    """下載費用報銷匯入範本 Excel"""
    xlsx = service.generate_import_template()
    return StreamingResponse(
        iter([xlsx]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="expense_import_template.xlsx"'},
    )


@router.post("/import")
async def import_expenses(
    file: UploadFile = File(...),
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(optional_auth()),
):
    """匯入費用報銷 Excel"""
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 .xlsx/.xls 格式")
    content = await file.read()
    uid = current_user.id if current_user else None
    result = await service.import_from_excel(content, user_id=uid)
    return SuccessResponse(
        data=result,
        message=f"匯入完成: {result['created']} 新增, {result['skipped']} 跳過",
    )


@router.post("/receipt-image")
async def get_receipt_image(
    params: ERPIdRequest,
    service: ExpenseInvoiceService = Depends(get_service(ExpenseInvoiceService)),
    current_user: User = Depends(require_auth()),
):
    """取得收據影像 (POST-only 安全策略)"""
    invoice = await service.get_by_id(params.id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")
    if not invoice.receipt_image_path:
        raise HTTPException(status_code=404, detail="此發票無收據影像")

    # 支援相對路徑 (receipts/xxx.jpg) 與絕對路徑 (向後相容)
    path = invoice.receipt_image_path
    if not os.path.isabs(path):
        path = str(Path("uploads") / path)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="收據檔案不存在")

    return FileResponse(path=path)


@router.post("/suggest-category")
async def suggest_category(
    request: Request,
    current_user: User = Depends(optional_auth()),
):
    """Gemma 4 AI 費用分類建議 — 根據品名/賣方自動推薦分類"""
    import httpx
    body = await request.json()
    item_name = body.get("item_name", "")
    seller = body.get("seller", "")

    if not item_name and not seller:
        return SuccessResponse(data={"category": None, "confidence": 0})

    prompt = (
        f"根據以下發票資訊，從選項中選擇最適合的費用分類，只回答分類名稱。\n"
        f"選項：交通費、差旅費、文具及印刷、郵電費、水電費、保險費、租金、"
        f"維修費、雜費、設備採購、外包及勞務、訓練費、材料費、報銷及費用、其他\n"
        f"品名：{item_name}\n"
        f"賣方：{seller}\n"
        f"分類："
    )

    try:
        from app.services.ai.ai_config import get_ai_config
        config = get_ai_config()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{config.ollama_base_url}/api/chat",
                json={
                    "model": config.ollama_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.1, "num_predict": 20},
                },
                timeout=30,
            )
            data = resp.json()
            suggestion = data.get("message", {}).get("content", "").strip()
            # 驗證是否為有效分類
            valid = [
                "交通費", "差旅費", "文具及印刷", "郵電費", "水電費",
                "保險費", "租金", "維修費", "雜費", "設備採購",
                "外包及勞務", "訓練費", "材料費", "報銷及費用", "其他",
            ]
            category = suggestion if suggestion in valid else None
            return SuccessResponse(data={
                "category": category,
                "raw": suggestion,
                "confidence": 1.0 if category else 0.5,
            })
    except Exception as e:
        logger.warning(f"AI 分類建議失敗: {e}")
        return SuccessResponse(data={"category": None, "confidence": 0})
