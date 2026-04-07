"""
檔案管理模組 - 下載端點

包含: /{file_id}/download
"""

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import DocumentAttachment, User
from app.core.dependencies import require_auth
from app.core.exceptions import ForbiddenException

from .common import check_document_access, UPLOAD_BASE_DIR

router = APIRouter()


@router.post("/{file_id}/download", summary="下載檔案")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth())
):
    """
    下載指定檔案（POST-only 資安機制）

    🔒 權限規則：
    - 需要登入認證
    - 管理員可下載所有檔案
    - 一般使用者只能下載關聯專案公文的附件
    """
    result = await db.execute(
        select(DocumentAttachment).where(DocumentAttachment.id == file_id)
    )
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="檔案不存在"
        )

    if attachment.document_id:
        has_access = await check_document_access(db, attachment.document_id, current_user)
        if not has_access:
            raise ForbiddenException("您沒有權限下載此檔案")

    # 解析實際檔案路徑 — DB 可能存 relative_path 或含 UPLOAD_BASE_DIR 前綴
    stored_path = attachment.file_path or ''
    if stored_path.startswith(UPLOAD_BASE_DIR):
        actual_path = stored_path  # 舊資料：已含完整路徑
    else:
        actual_path = os.path.join(UPLOAD_BASE_DIR, stored_path)  # 新資料：相對路徑

    if not stored_path or not os.path.exists(actual_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="檔案不存在於伺服器"
        )

    download_filename = attachment.original_name or attachment.file_name or 'download'

    return FileResponse(
        path=actual_path,
        filename=download_filename,
        media_type=attachment.mime_type or 'application/octet-stream'
    )
