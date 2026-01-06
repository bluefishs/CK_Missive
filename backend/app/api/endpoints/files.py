"""
檔案管理API端點 (POST-only 資安機制 + 結構化儲存)

變更記錄：
- 2026-01-06: 實作 POST-only 資安規範，移除 DELETE 方法
- 2026-01-06: 新增結構化目錄儲存 (年/月/公文ID)
- 2026-01-06: 新增 SHA256 校驗碼、上傳者追蹤
- 2026-01-06: 新增檔案類型白名單驗證
- 2026-01-06: 支援網路磁碟路徑設定
"""
import os
import uuid
import hashlib
import aiofiles
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import FileResponse
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.database import get_async_db
from app.extended.models import DocumentAttachment, User, OfficialDocument
from app.api.endpoints.auth import get_current_user
from app.core.config import settings

router = APIRouter()

# ============================================================================
# 設定常數
# ============================================================================

# 檔案儲存根目錄（支援環境變數設定網路路徑）
UPLOAD_BASE_DIR = getattr(settings, 'ATTACHMENT_STORAGE_PATH', None) or os.getenv(
    'ATTACHMENT_STORAGE_PATH',
    'uploads'
)

# 允許的檔案類型白名單
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
    '.zip', '.rar', '.7z',
    '.txt', '.csv', '.xml', '.json',
    '.dwg', '.dxf',  # CAD 檔案
    '.shp', '.kml', '.kmz',  # GIS 檔案
}

# 檔案大小限制 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# 確保根目錄存在
os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)


# ============================================================================
# 工具函數
# ============================================================================

def get_structured_path(document_id: Optional[int], filename: str) -> tuple[str, str]:
    """
    生成結構化儲存路徑

    格式: {base}/{year}/{month}/doc_{document_id}/{uuid}_{original_name}

    Returns:
        tuple: (完整檔案路徑, 相對路徑)
    """
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')

    # 生成 UUID 前綴
    file_uuid = str(uuid.uuid4())[:8]

    # 安全處理檔案名稱
    safe_filename = "".join(c for c in filename if c.isalnum() or c in '._-').strip()
    if not safe_filename:
        safe_filename = 'unnamed'

    # 組合檔案名稱
    unique_filename = f"{file_uuid}_{safe_filename}"

    # 建立目錄結構
    if document_id:
        relative_dir = os.path.join(year, month, f"doc_{document_id}")
    else:
        relative_dir = os.path.join(year, month, "temp")

    full_dir = os.path.join(UPLOAD_BASE_DIR, relative_dir)
    os.makedirs(full_dir, exist_ok=True)

    relative_path = os.path.join(relative_dir, unique_filename)
    full_path = os.path.join(UPLOAD_BASE_DIR, relative_path)

    return full_path, relative_path


def calculate_checksum(content: bytes) -> str:
    """計算 SHA256 校驗碼"""
    return hashlib.sha256(content).hexdigest()


def validate_file_extension(filename: str) -> bool:
    """驗證檔案副檔名是否在白名單中"""
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """取得檔案副檔名"""
    return os.path.splitext(filename or '')[1].lower()


# ============================================================================
# API 端點 (POST-only 資安機制)
# ============================================================================

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
        # 檔案類型驗證
        if not validate_file_extension(file.filename or ''):
            errors.append(f"檔案 {file.filename} 類型不允許")
            continue

        # 讀取檔案內容
        try:
            content = await file.read()
        except Exception as e:
            errors.append(f"讀取檔案 {file.filename} 失敗: {str(e)}")
            continue

        # 檔案大小驗證
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            errors.append(f"檔案 {file.filename} 超過大小限制 (50MB)")
            continue

        # 計算校驗碼
        checksum = calculate_checksum(content)

        # 生成結構化路徑
        file_path, relative_path = get_structured_path(document_id, file.filename or 'unnamed')

        # 儲存檔案
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
        except Exception as e:
            errors.append(f"儲存檔案 {file.filename} 失敗: {str(e)}")
            continue

        # 建立附件記錄
        attachment_id = None
        if document_id:
            try:
                attachment = DocumentAttachment(
                    document_id=document_id,
                    file_name=file.filename or 'unnamed',
                    file_path=file_path,
                    file_size=file_size,
                    mime_type=file.content_type,
                    # 新增欄位
                    original_name=file.filename,
                    storage_type='local',
                    checksum=checksum,
                    uploaded_by=current_user.id if current_user else None
                )
                db.add(attachment)
                await db.commit()
                await db.refresh(attachment)
                attachment_id = attachment.id
            except Exception as e:
                # 如果資料庫失敗，清理檔案
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


@router.post("/{file_id}/download", summary="下載檔案")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    下載指定檔案（POST-only 資安機制）
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

    if not attachment.file_path or not os.path.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="檔案不存在於伺服器"
        )

    # 使用原始檔名作為下載檔名
    download_filename = attachment.original_name or attachment.file_name or 'download'

    return FileResponse(
        path=attachment.file_path,
        filename=download_filename,
        media_type=attachment.mime_type or 'application/octet-stream'
    )


@router.post("/{file_id}/delete", summary="刪除檔案")
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    刪除指定檔案（POST-only 資安機制）

    - 同時刪除實體檔案與資料庫記錄
    - 需要登入認證
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

    deleted_filename = attachment.file_name or attachment.original_name or 'unknown'

    # 刪除實體檔案
    if attachment.file_path and os.path.exists(attachment.file_path):
        try:
            os.remove(attachment.file_path)
        except Exception as e:
            # 記錄錯誤但繼續刪除資料庫記錄
            print(f"警告：刪除實體檔案失敗: {str(e)}")

    # 刪除資料庫記錄
    await db.execute(
        delete(DocumentAttachment).where(DocumentAttachment.id == file_id)
    )
    await db.commit()

    return {
        "success": True,
        "message": f"檔案 {deleted_filename} 刪除成功",
        "deleted_by": current_user.username if current_user else None
    }


@router.post("/document/{document_id}", summary="取得文件附件列表")
async def get_document_attachments(
    document_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得指定文件的所有附件（POST-only 資安機制）
    """
    result = await db.execute(
        select(DocumentAttachment)
        .where(DocumentAttachment.document_id == document_id)
        .order_by(DocumentAttachment.created_at.desc())
    )
    attachments = result.scalars().all()

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
                "created_at": att.created_at.isoformat() if att.created_at else None
            }
            for att in attachments
        ]
    }


@router.post("/verify/{file_id}", summary="驗證檔案完整性")
async def verify_file_integrity(
    file_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    驗證檔案 SHA256 校驗碼是否一致
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

    if not attachment.file_path or not os.path.exists(attachment.file_path):
        return {
            "success": False,
            "file_id": file_id,
            "status": "file_missing",
            "message": "檔案不存在於伺服器"
        }

    # 讀取檔案並計算校驗碼
    try:
        async with aiofiles.open(attachment.file_path, 'rb') as f:
            content = await f.read()
        current_checksum = calculate_checksum(content)
    except Exception as e:
        return {
            "success": False,
            "file_id": file_id,
            "status": "read_error",
            "message": f"讀取檔案失敗: {str(e)}"
        }

    stored_checksum = getattr(attachment, 'checksum', None)

    if not stored_checksum:
        return {
            "success": True,
            "file_id": file_id,
            "status": "no_checksum",
            "message": "檔案無儲存校驗碼，無法驗證",
            "current_checksum": current_checksum
        }

    is_valid = current_checksum == stored_checksum

    return {
        "success": True,
        "file_id": file_id,
        "status": "valid" if is_valid else "corrupted",
        "is_valid": is_valid,
        "stored_checksum": stored_checksum,
        "current_checksum": current_checksum,
        "message": "檔案完整性驗證通過" if is_valid else "警告：檔案可能已損壞或被修改"
    }


@router.post("/storage-info", summary="取得儲存資訊")
async def get_storage_info(
    current_user: User = Depends(get_current_user)
):
    """
    取得檔案儲存系統資訊
    """
    import shutil

    storage_path = Path(UPLOAD_BASE_DIR)

    # 計算目錄大小
    total_size = 0
    file_count = 0

    if storage_path.exists():
        for f in storage_path.rglob('*'):
            if f.is_file():
                total_size += f.stat().st_size
                file_count += 1

    # 取得磁碟空間資訊
    try:
        disk_usage = shutil.disk_usage(UPLOAD_BASE_DIR)
        disk_info = {
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "usage_percent": round(disk_usage.used / disk_usage.total * 100, 1)
        }
    except:
        disk_info = None

    return {
        "success": True,
        "storage_path": str(storage_path.absolute()),
        "storage_type": "network" if str(storage_path).startswith(('\\\\', '//', 'Z:', 'Y:')) else "local",
        "total_files": file_count,
        "total_size_mb": round(total_size / (1024**2), 2),
        "allowed_extensions": sorted(list(ALLOWED_EXTENSIONS)),
        "max_file_size_mb": MAX_FILE_SIZE / (1024**2),
        "disk_info": disk_info
    }
