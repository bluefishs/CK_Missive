"""
檔案管理模組 - 上傳端點

包含: /upload
"""

import os
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import DocumentAttachment, User
from app.api.endpoints.auth import get_current_user

from .common import (
    validate_file_extension, calculate_checksum, get_structured_path,
    MAX_FILE_SIZE, STORAGE_TYPE,
)

router = APIRouter()


@router.post("/upload", summary="上傳檔案")
async def upload_files(
    files: List[UploadFile] = File(...),
    document_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    上傳檔案並儲存到檔案系統（結構化目錄）

    - 支援多檔案同時上傳
    - 自動計算 SHA256 校驗碼
    - 記錄上傳者資訊
    - 檔案類型白名單驗證
    - 檔案大小限制 50MB
    """
    uploaded_files = []
    errors = []

    for file in files:
        if not validate_file_extension(file.filename or ''):
            errors.append(f"檔案 {file.filename} 類型不允許")
            continue

        try:
            content = await file.read()
        except Exception as e:
            errors.append(f"讀取檔案 {file.filename} 失敗: {str(e)}")
            continue

        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            errors.append(f"檔案 {file.filename} 超過大小限制 (50MB)")
            continue

        checksum = calculate_checksum(content)
        file_path, relative_path = get_structured_path(document_id, file.filename or 'unnamed')

        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
        except Exception as e:
            errors.append(f"儲存檔案 {file.filename} 失敗: {str(e)}")
            continue

        attachment_id = None
        if document_id:
            try:
                attachment = DocumentAttachment(
                    document_id=document_id,
                    file_name=file.filename or 'unnamed',
                    file_path=file_path,
                    file_size=file_size,
                    mime_type=file.content_type,
                    original_name=file.filename,
                    storage_type=STORAGE_TYPE,
                    checksum=checksum,
                    uploaded_by=current_user.id if current_user else None
                )
                db.add(attachment)
                await db.commit()
                await db.refresh(attachment)
                attachment_id = attachment.id
            except Exception as e:
                try:
                    os.remove(file_path)
                except:
                    pass
                errors.append(f"建立附件記錄失敗: {str(e)}")
                continue

        uploaded_files.append({
            "id": attachment_id,
            "filename": file.filename,
            "original_name": file.filename,
            "size": file_size,
            "content_type": file.content_type,
            "checksum": checksum,
            "storage_path": relative_path,
            "uploaded_by": current_user.username if current_user else None
        })

    result = {
        "success": len(uploaded_files) > 0,
        "message": f"成功上傳 {len(uploaded_files)} 個檔案",
        "files": uploaded_files
    }

    if errors:
        result["errors"] = errors
        result["message"] += f"，{len(errors)} 個檔案失敗"

    return result
