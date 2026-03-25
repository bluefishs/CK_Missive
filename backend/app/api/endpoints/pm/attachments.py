"""PM 案件報價紀錄附件 API

仿照 documents 附件機制，為 PM 案件提供報價單上傳/列表/下載/刪除。

端點：
- POST /attachments/{case_code}/upload — 上傳報價單
- POST /attachments/{case_code}/list — 列表
- POST /attachments/{attachment_id}/download — 下載
- POST /attachments/{attachment_id}/delete — 刪除
"""
import hashlib
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth, get_async_db
from app.extended.models import User
from app.extended.models.pm import PMCaseAttachment

logger = logging.getLogger(__name__)
router = APIRouter()

# 儲存根目錄
UPLOAD_ROOT = os.environ.get("PM_ATTACHMENT_DIR", "uploads/pm_attachments")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.jpg', '.jpeg', '.png', '.gif',
    '.zip', '.rar', '.7z',
    '.odt', '.ods',
}


def _validate_extension(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@router.post("/attachments/{case_code}/upload", summary="上傳報價單")
async def upload_quotation_files(
    case_code: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """上傳一或多個報價單檔案"""
    uploaded = []
    errors = []

    for file in files:
        if not file.filename:
            errors.append("檔案名稱為空")
            continue

        if not _validate_extension(file.filename):
            errors.append(f"不支援的檔案類型: {file.filename}")
            continue

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            errors.append(f"檔案過大: {file.filename} ({len(content) / 1024 / 1024:.1f}MB)")
            continue

        # 計算 checksum
        checksum = hashlib.sha256(content).hexdigest()

        # 結構化路徑
        now = datetime.now()
        dir_path = os.path.join(UPLOAD_ROOT, case_code, now.strftime("%Y%m"))
        os.makedirs(dir_path, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        full_path = os.path.join(dir_path, safe_name)

        with open(full_path, "wb") as f:
            f.write(content)

        attachment = PMCaseAttachment(
            case_code=case_code,
            file_name=safe_name,
            file_path=full_path,
            file_size=len(content),
            mime_type=file.content_type,
            original_name=file.filename,
            checksum=checksum,
            uploaded_by=current_user.id,
        )
        db.add(attachment)
        uploaded.append({
            "file_name": file.filename,
            "file_size": len(content),
        })

    await db.commit()
    logger.info(f"PM 附件上傳: case_code={case_code}, 成功={len(uploaded)}, 失敗={len(errors)}")

    return {
        "success": True,
        "files": uploaded,
        "errors": errors,
        "total_uploaded": len(uploaded),
    }


@router.post("/attachments/{case_code}/list", summary="列出報價紀錄附件")
async def list_quotation_attachments(
    case_code: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """取得指定案號的所有報價單附件"""
    result = await db.execute(
        select(PMCaseAttachment)
        .where(PMCaseAttachment.case_code == case_code)
        .order_by(PMCaseAttachment.created_at.desc())
    )
    attachments = result.scalars().all()

    return {
        "success": True,
        "attachments": [
            {
                "id": a.id,
                "file_name": a.original_name or a.file_name,
                "file_size": a.file_size,
                "mime_type": a.mime_type,
                "notes": a.notes,
                "uploaded_by": a.uploaded_by,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in attachments
        ],
        "total": len(attachments),
    }


@router.post("/attachments/{attachment_id}/download", summary="下載報價單")
async def download_quotation_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """下載指定附件"""
    result = await db.execute(
        select(PMCaseAttachment).where(PMCaseAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    if not os.path.exists(attachment.file_path):
        raise HTTPException(status_code=404, detail="檔案已遺失")

    return FileResponse(
        path=attachment.file_path,
        filename=attachment.original_name or attachment.file_name,
        media_type=attachment.mime_type or "application/octet-stream",
    )


@router.post("/attachments/{attachment_id}/delete", summary="刪除報價單")
async def delete_quotation_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """刪除指定附件（含檔案）"""
    result = await db.execute(
        select(PMCaseAttachment).where(PMCaseAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    # 刪除實體檔案
    if os.path.exists(attachment.file_path):
        try:
            os.remove(attachment.file_path)
        except OSError as e:
            logger.warning(f"刪除檔案失敗: {attachment.file_path}: {e}")

    await db.execute(
        delete(PMCaseAttachment).where(PMCaseAttachment.id == attachment_id)
    )
    await db.commit()

    return {"success": True, "message": "附件已刪除", "deleted_id": attachment_id}
