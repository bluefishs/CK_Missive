"""費用報銷發票 API 端點 (POST-only)"""
import os
import uuid
import logging
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.core.dependencies import get_service, optional_auth, require_auth, require_permission
from app.extended.models import User
from app.services.expense_invoice_service import ExpenseInvoiceService
from app.schemas.erp.expense import (
    ExpenseInvoiceCreate,
    ExpenseInvoiceQuery,
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
        items=items, total=total, page=(params.skip // params.limit) + 1, limit=params.limit
    )


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
