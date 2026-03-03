"""
檔案管理模組 - 管理端點

包含: /{file_id}/delete, /document/{document_id}, /verify/{file_id}

@version 2.0.0 - 遷移至 Repository 模式
@date 2026-02-28
"""

import os
import logging

import aiofiles

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import User
from app.core.dependencies import require_auth
from app.core.exceptions import ForbiddenException
from app.repositories.attachment_repository import AttachmentRepository

from .common import check_document_access, calculate_checksum

router = APIRouter()


def _get_attachment_repo(db: AsyncSession = Depends(get_async_db)) -> AttachmentRepository:
    return AttachmentRepository(db)


@router.post("/{file_id}/delete", summary="刪除檔案")
async def delete_file(
    file_id: int,
    repo: AttachmentRepository = Depends(_get_attachment_repo),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """
    刪除指定檔案（POST-only 資安機制）

    🔒 權限規則：
    - 需要登入認證
    - 管理員可刪除所有檔案
    - 一般使用者只能刪除關聯專案公文的附件
    """
    attachment = await repo.get_by_id(file_id)

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="檔案不存在",
        )

    if attachment.document_id:
        has_access = await check_document_access(db, attachment.document_id, current_user)
        if not has_access:
            raise ForbiddenException("您沒有權限刪除此檔案")

    deleted_filename = attachment.file_name or attachment.original_name or 'unknown'

    if attachment.file_path and os.path.exists(attachment.file_path):
        try:
            os.remove(attachment.file_path)
        except Exception as e:
            logger.warning(f"刪除實體檔案失敗: {str(e)}")

    await repo.delete(file_id)
    await db.commit()

    return {
        "success": True,
        "message": f"檔案 {deleted_filename} 刪除成功",
        "deleted_by": current_user.username if current_user else None,
    }


@router.post("/document/{document_id}", summary="取得文件附件列表")
async def get_document_attachments(
    document_id: int,
    repo: AttachmentRepository = Depends(_get_attachment_repo),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """
    取得指定文件的所有附件（POST-only 資安機制）

    🔒 權限規則：
    - 需要登入認證
    - 管理員可查看所有公文附件
    - 一般使用者只能查看關聯專案公文的附件
    """
    has_access = await check_document_access(db, document_id, current_user)
    if not has_access:
        raise ForbiddenException("您沒有權限查看此公文的附件")

    attachments = await repo.get_by_document_id(document_id)

    return {
        "success": True,
        "document_id": document_id,
        "total": len(attachments),
        "attachments": [
            {
                "id": att.id,
                "filename": att.file_name,
                "original_filename": getattr(att, 'original_name', None) or att.file_name,
                "file_size": att.file_size,
                "content_type": att.mime_type,
                "storage_type": getattr(att, 'storage_type', 'local'),
                "checksum": getattr(att, 'checksum', None),
                "uploaded_at": att.created_at.isoformat() if att.created_at else None,
                "uploaded_by": getattr(att, 'uploaded_by', None),
                "created_at": att.created_at.isoformat() if att.created_at else None,
            }
            for att in attachments
        ],
    }


@router.post("/verify/{file_id}", summary="驗證檔案完整性")
async def verify_file_integrity(
    file_id: int,
    repo: AttachmentRepository = Depends(_get_attachment_repo),
    current_user: User = Depends(require_auth()),
):
    """
    驗證檔案 SHA256 校驗碼是否一致。
    需要認證。
    """
    attachment = await repo.get_by_id(file_id)

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="檔案不存在",
        )

    if not attachment.file_path or not os.path.exists(attachment.file_path):
        return {
            "success": False,
            "file_id": file_id,
            "status": "file_missing",
            "message": "檔案不存在於伺服器",
        }

    try:
        async with aiofiles.open(attachment.file_path, 'rb') as f:
            content = await f.read()
        current_checksum = calculate_checksum(content)
    except Exception as e:
        return {
            "success": False,
            "file_id": file_id,
            "status": "read_error",
            "message": "讀取檔案失敗",
        }

    stored_checksum = getattr(attachment, 'checksum', None)

    if not stored_checksum:
        return {
            "success": True,
            "file_id": file_id,
            "status": "no_checksum",
            "message": "檔案無儲存校驗碼，無法驗證",
            "current_checksum": current_checksum,
        }

    is_valid = current_checksum == stored_checksum

    return {
        "success": True,
        "file_id": file_id,
        "status": "valid" if is_valid else "corrupted",
        "is_valid": is_valid,
        "stored_checksum": stored_checksum,
        "current_checksum": current_checksum,
        "message": "檔案完整性驗證通過" if is_valid else "警告：檔案可能已損壞或被修改",
    }
