"""
桃園派工管理 - 附件管理 API (POST-only 資安規範)

@version 1.0.0
@date 2026-01-22
"""
from typing import List
from .common import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    FileResponse,
    AsyncSession,
    select,
    get_async_db,
    require_auth,
    settings,
    os,
    uuid,
    hashlib,
    aiofiles,
    datetime,
    TaoyuanDispatchOrder,
    TaoyuanDispatchAttachment,
    DispatchAttachment,
    DispatchAttachmentListResponse,
    DispatchAttachmentUploadResult,
    DispatchAttachmentDeleteResult,
    DispatchAttachmentVerifyResult,
)

router = APIRouter()

# 附件儲存設定
ATTACHMENT_STORAGE_PATH = getattr(settings, 'ATTACHMENT_STORAGE_PATH', None) or os.getenv('ATTACHMENT_STORAGE_PATH', 'uploads')
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 允許的副檔名白名單
ALLOWED_EXTENSIONS = {
    # 文件
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    # 圖片
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
    # 壓縮
    '.zip', '.rar', '.7z',
    # 資料
    '.txt', '.csv', '.xml', '.json',
    # 設計
    '.dwg', '.dxf',
    # 地理
    '.shp', '.kml', '.kmz',
}


def _validate_file_extension(filename: str) -> bool:
    """驗證檔案副檔名"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def _calculate_checksum(content: bytes) -> str:
    """計算 SHA256 校驗碼"""
    return hashlib.sha256(content).hexdigest()


def _get_structured_path(dispatch_order_id: int, filename: str) -> tuple:
    """
    生成結構化儲存路徑
    格式: {base}/{year}/{month}/dispatch_{id}/{uuid}_{filename}
    """
    now = datetime.now()
    year_month = now.strftime("%Y/%m")
    unique_prefix = str(uuid.uuid4())[:8]
    safe_filename = f"{unique_prefix}_{filename}"

    relative_path = f"{year_month}/dispatch_{dispatch_order_id}/{safe_filename}"
    full_path = os.path.join(ATTACHMENT_STORAGE_PATH, relative_path)

    return full_path, relative_path


@router.post("/dispatch/{dispatch_order_id}/attachments/upload", summary="上傳派工單附件")
async def upload_dispatch_attachments(
    dispatch_order_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
) -> DispatchAttachmentUploadResult:
    """
    上傳派工單附件（支援多檔案）

    - 檔案類型白名單驗證
    - 檔案大小限制 50MB
    - 自動計算 SHA256 校驗碼
    - 結構化目錄儲存
    """
    # 驗證派工單存在
    dispatch_query = select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_order_id)
    result = await db.execute(dispatch_query)
    dispatch = result.scalar_one_or_none()

    if not dispatch:
        raise HTTPException(status_code=404, detail=f"派工單 {dispatch_order_id} 不存在")

    uploaded_files = []
    errors = []

    for file in files:
        try:
            # 驗證副檔名
            if not _validate_file_extension(file.filename):
                errors.append(f"檔案 {file.filename} 副檔名不在允許清單內")
                continue

            # 讀取檔案內容
            content = await file.read()

            # 驗證檔案大小
            if len(content) > MAX_FILE_SIZE:
                errors.append(f"檔案 {file.filename} 超過 50MB 限制")
                continue

            # 計算校驗碼
            checksum = _calculate_checksum(content)

            # 生成儲存路徑
            full_path, relative_path = _get_structured_path(dispatch_order_id, file.filename)

            # 建立目錄
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # 寫入檔案
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(content)

            # 建立資料庫記錄
            attachment = TaoyuanDispatchAttachment(
                dispatch_order_id=dispatch_order_id,
                file_name=os.path.basename(full_path),
                file_path=relative_path,
                file_size=len(content),
                mime_type=file.content_type,
                storage_type='local',
                original_name=file.filename,
                checksum=checksum,
                uploaded_by=current_user.id if current_user else None,
            )
            db.add(attachment)
            await db.flush()

            uploaded_files.append({
                'id': attachment.id,
                'filename': attachment.file_name,
                'original_name': file.filename,
                'size': len(content),
                'content_type': file.content_type,
                'checksum': checksum,
                'storage_path': relative_path,
                'uploaded_by': current_user.username if current_user else None,
            })

        except Exception as e:
            errors.append(f"上傳 {file.filename} 失敗: {str(e)}")

    await db.commit()

    return DispatchAttachmentUploadResult(
        success=len(errors) == 0,
        message=f"成功上傳 {len(uploaded_files)} 個檔案" if uploaded_files else "上傳失敗",
        files=uploaded_files,
        errors=errors,
    )


@router.post("/dispatch/{dispatch_order_id}/attachments/list", summary="取得派工單附件列表")
async def get_dispatch_attachments(
    dispatch_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
) -> DispatchAttachmentListResponse:
    """取得指定派工單的所有附件"""
    # 驗證派工單存在
    dispatch_query = select(TaoyuanDispatchOrder).where(TaoyuanDispatchOrder.id == dispatch_order_id)
    result = await db.execute(dispatch_query)
    dispatch = result.scalar_one_or_none()

    if not dispatch:
        raise HTTPException(status_code=404, detail=f"派工單 {dispatch_order_id} 不存在")

    # 查詢附件
    attachments_query = select(TaoyuanDispatchAttachment).where(
        TaoyuanDispatchAttachment.dispatch_order_id == dispatch_order_id
    ).order_by(TaoyuanDispatchAttachment.created_at.desc())

    attachments_result = await db.execute(attachments_query)
    attachments = attachments_result.scalars().all()

    return DispatchAttachmentListResponse(
        success=True,
        dispatch_order_id=dispatch_order_id,
        total=len(attachments),
        attachments=[DispatchAttachment.model_validate(a) for a in attachments],
    )


@router.post("/dispatch/attachments/{attachment_id}/download", summary="下載派工單附件")
async def download_dispatch_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
) -> FileResponse:
    """下載指定附件（POST-only 資安機制）"""
    # 查詢附件
    attachment_query = select(TaoyuanDispatchAttachment).where(TaoyuanDispatchAttachment.id == attachment_id)
    result = await db.execute(attachment_query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(status_code=404, detail=f"附件 {attachment_id} 不存在")

    # 組合完整路徑
    full_path = os.path.join(ATTACHMENT_STORAGE_PATH, attachment.file_path)

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="檔案不存在於儲存系統")

    return FileResponse(
        path=full_path,
        filename=attachment.original_name or attachment.file_name,
        media_type=attachment.mime_type or 'application/octet-stream',
    )


@router.post("/dispatch/attachments/{attachment_id}/delete", summary="刪除派工單附件")
async def delete_dispatch_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
) -> DispatchAttachmentDeleteResult:
    """刪除指定附件（POST-only 資安機制）"""
    # 查詢附件
    attachment_query = select(TaoyuanDispatchAttachment).where(TaoyuanDispatchAttachment.id == attachment_id)
    result = await db.execute(attachment_query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(status_code=404, detail=f"附件 {attachment_id} 不存在")

    # 刪除實體檔案
    full_path = os.path.join(ATTACHMENT_STORAGE_PATH, attachment.file_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except Exception:
            # 記錄錯誤但繼續刪除資料庫記錄
            pass

    # 刪除資料庫記錄
    await db.delete(attachment)
    await db.commit()

    return DispatchAttachmentDeleteResult(
        success=True,
        message=f"附件 {attachment_id} 已刪除",
    )


@router.post("/dispatch/attachments/{attachment_id}/verify", summary="驗證附件完整性")
async def verify_dispatch_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(require_auth())
) -> DispatchAttachmentVerifyResult:
    """驗證 SHA256 校驗碼"""
    # 查詢附件
    attachment_query = select(TaoyuanDispatchAttachment).where(TaoyuanDispatchAttachment.id == attachment_id)
    result = await db.execute(attachment_query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(status_code=404, detail=f"附件 {attachment_id} 不存在")

    # 組合完整路徑
    full_path = os.path.join(ATTACHMENT_STORAGE_PATH, attachment.file_path)

    if not os.path.exists(full_path):
        return DispatchAttachmentVerifyResult(
            success=False,
            message="檔案不存在於儲存系統",
            valid=False,
            expected_checksum=attachment.checksum,
            actual_checksum=None,
        )

    # 計算實際校驗碼
    async with aiofiles.open(full_path, 'rb') as f:
        content = await f.read()
    actual_checksum = _calculate_checksum(content)

    is_valid = actual_checksum == attachment.checksum

    return DispatchAttachmentVerifyResult(
        success=True,
        message="檔案完整性驗證通過" if is_valid else "檔案完整性驗證失敗",
        valid=is_valid,
        expected_checksum=attachment.checksum,
        actual_checksum=actual_checksum,
    )
