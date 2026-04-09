"""費用報銷 IO 端點 — QR/OCR/智慧掃描/匯入匯出/收據/AI 分類"""
import os
import uuid
import logging
from decimal import Decimal
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse

from app.core.dependencies import get_service, optional_auth, require_auth
from app.extended.models import User
from app.services.expense_invoice_service import ExpenseInvoiceService
from app.schemas.erp.expense import ExpenseInvoiceQRScanRequest
from app.schemas.erp.requests import ERPIdRequest
from app.schemas.common import PaginatedResponse, SuccessResponse

logger = logging.getLogger(__name__)

RECEIPT_UPLOAD_DIR = Path(os.getenv("RECEIPT_UPLOAD_DIR", "uploads/receipts"))
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
MAX_RECEIPT_SIZE = 10 * 1024 * 1024  # 10MB

router = APIRouter()


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
    """上傳收據影像至費用發票"""
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
    """OCR 辨識發票影像，回傳結構化資訊供前端自動填入表單"""
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
    ext = Path(file.filename or "invoice.jpg").suffix or ".jpg"
    filename = f"ocr_{uuid.uuid4().hex}{ext}"
    file_path = RECEIPT_UPLOAD_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    from app.services.invoice_ocr_service import InvoiceOCRService
    ocr_service = InvoiceOCRService()
    try:
        result = ocr_service.parse_image(str(file_path))
    except Exception as e:
        logger.error(f"OCR 辨識失敗: {e}")
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="OCR 辨識過程發生錯誤")

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
    """智慧發票辨識 — QR 優先 + OCR 補充"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="僅支援 JPEG/PNG/WebP/HEIC 格式")

    content = await file.read()
    if len(content) > MAX_RECEIPT_SIZE:
        raise HTTPException(status_code=400, detail="檔案過大，上限 10MB")

    RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "scan.jpg").suffix or ".jpg"
    filename = f"scan_{uuid.uuid4().hex[:8]}{ext}"
    file_path = RECEIPT_UPLOAD_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    from app.services.invoice_recognizer import recognize_invoice
    recognition = recognize_invoice(str(file_path))

    result_data = recognition.to_dict()
    result_data["receipt_path"] = f"uploads/receipts/{filename}"

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
    """取得收據影像"""
    invoice = await service.get_by_id(params.id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")
    if not invoice.receipt_image_path:
        raise HTTPException(status_code=404, detail="此發票無收據影像")

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
    """Gemma 4 AI 費用分類建議"""
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
        from app.services.ai.core.ai_config import get_ai_config
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
