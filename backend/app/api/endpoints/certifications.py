"""
證照管理 API 端點

支援承辦同仁證照 CRUD 操作
所有端點皆使用 POST 方法（安全性考量）

變更記錄：
- 2026-01-26: 新增附件上傳端點 /{cert_id}/upload-attachment
- 2026-02-21: 遷移至 StaffCertificationRepository + UserRepository (v1.59.0)
"""
import os
import uuid
import hashlib
import logging
import aiofiles

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.db.database import get_async_db
from app.repositories import StaffCertificationRepository, UserRepository
from app.schemas.certification import (
    CertificationCreate,
    CertificationUpdate,
    CertificationResponse,
    CertificationListResponse,
    CertificationListParams,
    CertificationApiResponse,
    CertificationListApiResponse,
    CertificationStatsApiResponse,
    CertificationDeleteApiResponse,
)
from app.schemas.common import PaginationMeta
from app.api.response_helper import (
    success_response,
    error_response,
)
from app.core.config import settings

router = APIRouter()


@router.post("/create", response_model=CertificationApiResponse)
async def create_certification(
    data: CertificationCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    新增證照紀錄
    """
    try:
        # 檢查使用者是否存在
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(data.user_id)
        if not user:
            return error_response("找不到指定的使用者", code=404)

        # 建立證照紀錄
        cert_repo = StaffCertificationRepository(db)
        certification = await cert_repo.create({
            "user_id": data.user_id,
            "cert_type": data.cert_type,
            "cert_name": data.cert_name,
            "issuing_authority": data.issuing_authority,
            "cert_number": data.cert_number,
            "issue_date": data.issue_date,
            "expiry_date": data.expiry_date,
            "status": data.status,
            "notes": data.notes,
        })

        return success_response(
            data=CertificationResponse.model_validate(certification).model_dump(),
            message="證照新增成功"
        )

    except Exception as e:
        await db.rollback()
        return error_response(f"新增證照失敗: {str(e)}")


@router.post("/user/{user_id}/list", response_model=CertificationListApiResponse)
async def get_user_certifications(
    user_id: int,
    params: Optional[CertificationListParams] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得指定使用者的證照列表
    """
    try:
        if params is None:
            params = CertificationListParams()

        # 檢查使用者是否存在
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            return error_response("找不到指定的使用者", code=404)

        # 使用 Repository 進行篩選查詢
        cert_repo = StaffCertificationRepository(db)
        certifications, total = await cert_repo.filter_certifications(
            user_id=user_id,
            cert_type=params.cert_type,
            status=params.status,
            keyword=params.keyword,
            page=params.page,
            page_size=params.page_size,
        )

        # 轉換為回應格式
        items = [CertificationResponse.model_validate(c).model_dump() for c in certifications]

        return success_response(
            data={
                "items": items,
                "pagination": {
                    "total": total,
                    "page": params.page,
                    "page_size": params.page_size,
                    "total_pages": (total + params.page_size - 1) // params.page_size
                }
            }
        )

    except Exception as e:
        return error_response(f"取得證照列表失敗: {str(e)}")


@router.post("/{cert_id}/detail", response_model=CertificationApiResponse)
async def get_certification_detail(
    cert_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得證照詳情
    """
    try:
        cert_repo = StaffCertificationRepository(db)
        certification = await cert_repo.get_by_id(cert_id)

        if not certification:
            return error_response("找不到指定的證照", code=404)

        return success_response(
            data=CertificationResponse.model_validate(certification).model_dump()
        )

    except Exception as e:
        return error_response(f"取得證照詳情失敗: {str(e)}")


@router.post("/{cert_id}/update", response_model=CertificationApiResponse)
async def update_certification(
    cert_id: int,
    data: CertificationUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    更新證照紀錄
    """
    try:
        cert_repo = StaffCertificationRepository(db)
        certification = await cert_repo.get_by_id(cert_id)

        if not certification:
            return error_response("找不到指定的證照", code=404)

        # 更新非空欄位
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        update_data["updated_at"] = datetime.now()

        certification = await cert_repo.update(cert_id, update_data)

        return success_response(
            data=CertificationResponse.model_validate(certification).model_dump(),
            message="證照更新成功"
        )

    except Exception as e:
        await db.rollback()
        return error_response(f"更新證照失敗: {str(e)}")


@router.post("/{cert_id}/delete", response_model=CertificationDeleteApiResponse)
async def delete_certification(
    cert_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    刪除證照紀錄
    """
    try:
        cert_repo = StaffCertificationRepository(db)
        success = await cert_repo.delete(cert_id)

        if not success:
            return error_response("找不到指定的證照", code=404)

        return success_response(message="證照刪除成功")

    except Exception as e:
        await db.rollback()
        return error_response(f"刪除證照失敗: {str(e)}")


@router.post("/stats/{user_id}", response_model=CertificationStatsApiResponse)
async def get_certification_stats(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    取得使用者證照統計
    """
    try:
        # 檢查使用者是否存在
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if not user:
            return error_response("找不到指定的使用者", code=404)

        # 使用 Repository 取得統計
        cert_repo = StaffCertificationRepository(db)
        stats = await cert_repo.get_statistics(user_id)

        return success_response(data=stats)

    except Exception as e:
        return error_response(f"取得證照統計失敗: {str(e)}")


# ============================================================================
# 附件管理端點
# ============================================================================

# 證照附件儲存目錄
CERT_UPLOAD_DIR = getattr(settings, 'ATTACHMENT_STORAGE_PATH', None) or os.getenv(
    'ATTACHMENT_STORAGE_PATH', 'uploads'
)
CERT_UPLOAD_SUBDIR = 'certifications'

# 允許的檔案類型
ALLOWED_CERT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
MAX_CERT_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def calculate_checksum(content: bytes) -> str:
    """計算 SHA256 校驗碼（與公文附件統一機制）"""
    return hashlib.sha256(content).hexdigest()


def get_cert_upload_path(user_id: int, cert_id: int, filename: str) -> tuple[str, str]:
    """
    生成證照附件儲存路徑
    格式: {base}/certifications/user_{user_id}/{uuid}_{filename}
    Returns: (完整路徑, 相對路徑)
    """
    file_uuid = str(uuid.uuid4())[:8]
    safe_filename = "".join(c for c in filename if c.isalnum() or c in '._-').strip()
    if not safe_filename:
        safe_filename = 'cert_attachment'
    unique_filename = f"{file_uuid}_{safe_filename}"

    relative_dir = os.path.join(CERT_UPLOAD_SUBDIR, f"user_{user_id}")
    full_dir = os.path.join(CERT_UPLOAD_DIR, relative_dir)
    os.makedirs(full_dir, exist_ok=True)

    relative_path = os.path.join(relative_dir, unique_filename)
    full_path = os.path.join(CERT_UPLOAD_DIR, relative_path)

    return full_path, relative_path


@router.post("/{cert_id}/upload-attachment")
async def upload_certification_attachment(
    cert_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db)
):
    """
    上傳證照掃描檔附件

    - 支援格式: PDF, JPG, PNG, GIF, BMP, TIFF
    - 檔案大小限制: 10MB
    - 自動覆蓋舊附件
    """
    try:
        # 查詢證照
        cert_repo = StaffCertificationRepository(db)
        certification = await cert_repo.get_by_id(cert_id)

        if not certification:
            return error_response("找不到指定的證照", code=404)

        # 驗證檔案類型
        filename = file.filename or 'attachment'
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_CERT_EXTENSIONS:
            return error_response(
                f"不支援的檔案格式。允許格式: {', '.join(ALLOWED_CERT_EXTENSIONS)}"
            )

        # 讀取檔案內容
        content = await file.read()
        file_size = len(content)

        # 驗證檔案大小
        if file_size > MAX_CERT_FILE_SIZE:
            return error_response(f"檔案大小超過限制 (最大 10MB)")

        # 生成儲存路徑
        full_path, relative_path = get_cert_upload_path(
            certification.user_id, cert_id, filename
        )

        # 刪除舊附件（如果存在）
        if certification.attachment_path:
            old_path = os.path.join(CERT_UPLOAD_DIR, certification.attachment_path)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

        # 計算 SHA256 校驗碼（統一機制）
        checksum = calculate_checksum(content)

        # 儲存新檔案
        async with aiofiles.open(full_path, 'wb') as f:
            await f.write(content)

        # 更新資料庫
        certification.attachment_path = relative_path
        certification.updated_at = datetime.now()
        await db.commit()
        await db.refresh(certification)

        return success_response(
            data={
                "cert_id": cert_id,
                "attachment_path": relative_path,
                "filename": filename,
                "file_size": file_size,
                "checksum": checksum,
            },
            message="附件上傳成功"
        )

    except Exception as e:
        await db.rollback()
        return error_response(f"上傳附件失敗: {str(e)}")


@router.post("/{cert_id}/download-attachment")
async def download_certification_attachment(
    cert_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    下載證照附件
    """
    try:
        cert_repo = StaffCertificationRepository(db)
        certification = await cert_repo.get_by_id(cert_id)

        if not certification:
            return error_response("找不到指定的證照", code=404)

        if not certification.attachment_path:
            return error_response("此證照沒有附件")

        full_path = os.path.join(CERT_UPLOAD_DIR, certification.attachment_path)

        if not os.path.exists(full_path):
            return error_response("附件檔案不存在")

        # 取得檔名
        filename = os.path.basename(certification.attachment_path)
        # 移除 UUID 前綴
        if '_' in filename:
            filename = filename.split('_', 1)[1]

        return FileResponse(
            path=full_path,
            filename=filename,
            media_type='application/octet-stream'
        )

    except Exception as e:
        return error_response(f"下載附件失敗: {str(e)}")


@router.post("/{cert_id}/delete-attachment")
async def delete_certification_attachment(
    cert_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    刪除證照附件
    """
    try:
        cert_repo = StaffCertificationRepository(db)
        certification = await cert_repo.get_by_id(cert_id)

        if not certification:
            return error_response("找不到指定的證照", code=404)

        if not certification.attachment_path:
            return error_response("此證照沒有附件")

        # 刪除實體檔案
        full_path = os.path.join(CERT_UPLOAD_DIR, certification.attachment_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                logger.warning(f"刪除實體檔案失敗: {str(e)}")

        # 更新資料庫
        certification.attachment_path = None
        certification.updated_at = datetime.now()
        await db.commit()

        return success_response(message="附件刪除成功")

    except Exception as e:
        await db.rollback()
        return error_response(f"刪除附件失敗: {str(e)}")
