"""
檔案管理API端點 (非同步化)
"""
import os
import uuid
import aiofiles
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import FileResponse
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.database import get_async_db
from app.extended.models import DocumentAttachment, User
from app.api.endpoints.auth import get_current_user

router = APIRouter()

# 檔案儲存目錄
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", summary="上傳檔案")
async def upload_files(
    files: List[UploadFile] = File(...),
    document_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    上傳檔案並儲存到檔案系統
    支援多檔案同時上傳
    """
    uploaded_files = []

    for file in files:
        # 生成唯一檔案名
        file_extension = os.path.splitext(file.filename or '')[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # 儲存檔案
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"檔案儲存失敗: {str(e)}"
            )

        # 如果有指定文件ID，則建立附件記錄
        attachment_id = None
        if document_id:
            try:
                attachment = DocumentAttachment(
                    document_id=document_id,
                    file_name=file.filename or unique_filename,
                    file_path=file_path,
                    file_size=file.size or len(content),
                    mime_type=file.content_type
                )
                db.add(attachment)
                await db.commit()
                await db.refresh(attachment)
                attachment_id = attachment.id
            except Exception as e:
                # 如果資料庫失敗，清理檔案
                os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"建立附件記錄失敗: {str(e)}"
                )

        uploaded_files.append({
            "id": attachment_id,
            "filename": file.filename,
            "size": file.size if file.size is not None else len(content),
            "content_type": file.content_type,
            "file_path": unique_filename
        })

    return {
        "message": f"成功上傳 {len(files)} 個檔案",
        "files": uploaded_files
    }

@router.get("/{file_id}/download", summary="下載檔案")
async def download_file(file_id: int, db: AsyncSession = Depends(get_async_db)):
    """下載指定檔案"""
    result = await db.execute(
        select(DocumentAttachment).where(DocumentAttachment.id == file_id)
    )
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="檔案不存在"
        )

    if not attachment.file_path or not os.path.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="檔案不存在於伺服器"
        )

    return FileResponse(
        path=attachment.file_path,
        filename=attachment.file_name or 'unknown',
        media_type=attachment.mime_type or 'application/octet-stream'
    )

@router.delete("/{file_id}", summary="刪除檔案")
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """刪除指定檔案"""
    result = await db.execute(
        select(DocumentAttachment).where(DocumentAttachment.id == file_id)
    )
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="檔案不存在"
        )

    # 刪除實體檔案
    if attachment.file_path and os.path.exists(attachment.file_path):
        try:
            os.remove(attachment.file_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"刪除檔案失敗: {str(e)}"
            )

    # 刪除資料庫記錄
    await db.execute(delete(DocumentAttachment).where(DocumentAttachment.id == file_id))
    await db.commit()

    return {"message": f"檔案 {attachment.file_name} 刪除成功"}

@router.get("/document/{document_id}", summary="取得文件附件列表")
async def get_document_attachments(
    document_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """取得指定文件的所有附件"""
    result = await db.execute(
        select(DocumentAttachment)
        .where(DocumentAttachment.document_id == document_id)
    )
    attachments = result.scalars().all()

    return {
        "document_id": document_id,
        "attachments": [
            {
                "id": att.id,
                "filename": att.file_name,
                "original_filename": att.file_name,
                "file_size": att.file_size,
                "content_type": att.mime_type,
                "uploaded_at": att.created_at.isoformat() if att.created_at else None,
                "uploaded_by": None,
                "created_at": att.created_at.isoformat() if att.created_at else None
            }
            for att in attachments
        ]
    }
