"""電子發票同步 API 端點 (POST-only)

提供財政部電子發票自動同步管理功能:
- 手動觸發同步
- 查詢待核銷清單 (手機端)
- 上傳收據照片並關聯
- 查詢同步歷史
"""
import os
import uuid
import logging
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from app.core.dependencies import get_service, require_auth, require_admin
from app.extended.models import User
from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService
from app.schemas.erp.einvoice_sync import (
    EInvoiceSyncRequest,
    EInvoiceSyncLogQuery,
    PendingReceiptQuery,
)
from app.schemas.common import PaginatedResponse, SuccessResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 收據影像儲存目錄
RECEIPT_UPLOAD_DIR = Path(
    os.getenv("RECEIPT_UPLOAD_DIR", "uploads/receipts")
)


@router.post("/sync")
async def trigger_sync(
    params: EInvoiceSyncRequest,
    service: EInvoiceSyncService = Depends(get_service(EInvoiceSyncService)),
    current_user: User = Depends(require_admin()),
):
    """手動觸發電子發票同步 (管理員用)"""
    result = await service.sync_invoices(
        start_date=params.start_date,
        end_date=params.end_date,
    )
    return SuccessResponse(data=result, message="同步完成")


@router.post("/pending-list")
async def get_pending_receipt_list(
    params: PendingReceiptQuery,
    service: EInvoiceSyncService = Depends(get_service(EInvoiceSyncService)),
    current_user: User = Depends(require_auth()),
):
    """待核銷發票清單 (手機端報帳員使用)

    列出所有從財政部同步但尚未上傳收據的發票。
    """
    items, total = await service.get_pending_receipt_list(
        skip=params.skip, limit=params.limit
    )
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=(params.skip // params.limit) + 1,
        limit=params.limit,
    )


@router.post("/upload-receipt")
async def upload_receipt(
    invoice_id: int = Form(..., description="發票 ID"),
    case_code: str = Form(None, description="案號"),
    category: str = Form(None, description="費用分類"),
    file: UploadFile = File(..., description="收據影像"),
    service: EInvoiceSyncService = Depends(get_service(EInvoiceSyncService)),
    current_user: User = Depends(require_auth()),
):
    """上傳收據影像並關聯發票 — 報帳員核銷動作

    上傳收據照片後，發票狀態從 pending_receipt → pending (待審核)。
    """
    # 驗證檔案類型
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/heic"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的檔案格式: {file.content_type}，請上傳 JPEG/PNG/WebP/HEIC",
        )

    # 檔案大小限制 (10MB)
    MAX_RECEIPT_SIZE = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_RECEIPT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"檔案過大 ({len(content) // 1024 // 1024}MB)，上限為 10MB",
        )

    # 儲存檔案 (使用相對路徑，對應 /uploads StaticFiles mount)
    RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "receipt.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = RECEIPT_UPLOAD_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # 儲存相對路徑 (receipts/xxx.jpg)，前端透過 /uploads/ 前綴存取
    relative_path = f"receipts/{filename}"

    # 關聯發票
    user_id = current_user.id if current_user else None
    try:
        result = await service.attach_receipt(
            invoice_id=invoice_id,
            receipt_path=relative_path,
            case_code=case_code,
            category=category,
            user_id=user_id,
        )
    except ValueError as e:
        # 清理已上傳的檔案
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))

    if not result:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail="發票不存在")

    return SuccessResponse(data=result, message="收據上傳成功，發票已轉為待審核")


@router.post("/sync-logs")
async def get_sync_logs(
    params: EInvoiceSyncLogQuery,
    service: EInvoiceSyncService = Depends(get_service(EInvoiceSyncService)),
    current_user: User = Depends(require_auth()),
):
    """查詢同步歷史記錄"""
    items, total = await service.get_sync_logs(
        skip=params.skip, limit=params.limit
    )
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=(params.skip // params.limit) + 1,
        limit=params.limit,
    )
