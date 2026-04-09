"""資產管理 API 端點 (POST-only)"""
import os
import uuid
import logging
from pathlib import Path
from datetime import date

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse

from app.core.dependencies import get_service, optional_auth, require_auth
from app.extended.models import User
from app.services.erp.asset_service import AssetService
from app.schemas.erp.asset import (
    AssetCreateRequest,
    AssetUpdateRequest,
    AssetListRequest,
    AssetBatchInventoryRequest,
    AssetLogCreateRequest,
    AssetLogListRequest,
    AssetResponse,
    AssetLogResponse,
    AssetStatsResponse,
)
from app.schemas.erp.requests import ERPIdRequest
from app.schemas.common import PaginatedResponse, SuccessResponse

logger = logging.getLogger(__name__)

ASSET_PHOTO_DIR = Path(os.getenv("ASSET_PHOTO_DIR", "uploads/asset_photos"))
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10MB

router = APIRouter()


@router.post("/list")
async def list_assets(
    params: AssetListRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """資產列表 (多條件查詢)"""
    items, total = await service.list_assets(params)
    return PaginatedResponse.create(
        items=[AssetResponse.model_validate(i) for i in items],
        total=total,
        page=(params.skip // params.limit) + 1,
        limit=params.limit,
    )


@router.post("/create")
async def create_asset(
    data: AssetCreateRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(optional_auth()),
):
    """建立資產"""
    try:
        user_id = current_user.id if current_user else None
        result = await service.create_asset(data, user_id=user_id)
        return SuccessResponse(
            data=AssetResponse.model_validate(result),
            message="資產建立成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/detail")
async def get_asset_detail(
    params: ERPIdRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """取得資產詳情"""
    result = await service.get_asset(params.id)
    if not result:
        raise HTTPException(status_code=404, detail="資產不存在")
    return SuccessResponse(data=AssetResponse.model_validate(result))


@router.post("/detail-full")
async def get_asset_detail_full(
    req: ERPIdRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """資產完整詳情 (含關聯發票+案件)"""
    result = await service.get_asset_with_relations(req.id)
    if not result:
        raise HTTPException(status_code=404, detail="資產不存在")
    # Serialize the asset ORM object via response model
    from app.schemas.erp.asset import AssetResponse
    result["asset"] = AssetResponse.model_validate(result["asset"]).model_dump()
    return SuccessResponse(data=result)


@router.post("/update")
async def update_asset(
    params: AssetUpdateRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """更新資產"""
    result = await service.update_asset(params, user_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="資產不存在")
    return SuccessResponse(
        data=AssetResponse.model_validate(result),
        message="資產更新成功",
    )


@router.post("/delete")
async def delete_asset(
    params: ERPIdRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """刪除資產"""
    success = await service.delete_asset(params.id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="資產不存在")
    return SuccessResponse(message="資產刪除成功")


@router.post("/by-invoice")
async def get_assets_by_invoice(
    req: ERPIdRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """取得關聯到指定發票的資產"""
    items = await service.get_assets_by_invoice(req.id)
    return SuccessResponse(data=[AssetResponse.model_validate(a) for a in items])


@router.post("/stats")
async def get_asset_stats(
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """取得資產統計"""
    stats = await service.get_stats()
    return SuccessResponse(data=AssetStatsResponse(**stats))


@router.post("/export")
async def export_assets(
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """匯出資產清單 Excel"""
    xlsx_bytes = await service.export_assets_excel()
    filename = f"assets_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def import_assets(
    file: UploadFile = File(...),
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(optional_auth()),
):
    """匯入資產清單 Excel"""
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="僅支援 .xlsx/.xls 格式")

    content = await file.read()
    user_id = current_user.id if current_user else None
    result = await service.import_assets_excel(content, user_id=user_id)
    return SuccessResponse(
        data=result,
        message=f"匯入完成: {result['created']} 新增, {result['updated']} 更新",
    )


@router.post("/logs/list")
async def list_asset_logs(
    params: AssetLogListRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """取得資產行為紀錄列表"""
    items, total = await service.list_logs(params)
    return PaginatedResponse.create(
        items=[AssetLogResponse.model_validate(i) for i in items],
        total=total,
        page=(params.skip // params.limit) + 1,
        limit=params.limit,
    )


@router.post("/logs/create")
async def create_asset_log(
    data: AssetLogCreateRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(optional_auth()),
):
    """建立資產行為紀錄"""
    try:
        user_id = current_user.id if current_user else None
        result = await service.create_log(data, user_id=user_id)
        return SuccessResponse(
            data=AssetLogResponse.model_validate(result),
            message="行為紀錄建立成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/batch-inventory")
async def batch_inventory(
    params: AssetBatchInventoryRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(optional_auth()),
):
    """批次盤點"""
    user_id = current_user.id if current_user else None
    result = await service.batch_inventory(
        asset_ids=params.asset_ids,
        operator=params.operator,
        notes=params.notes,
        user_id=user_id,
    )
    return SuccessResponse(data=result)


@router.post("/import-template")
async def download_import_template(
    service: AssetService = Depends(get_service(AssetService)),
):
    """下載資產匯入範本 Excel"""
    xlsx_bytes = service.generate_import_template()
    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="asset_import_template.xlsx"'},
    )


@router.post("/export-inventory")
async def export_inventory_report(
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """匯出盤點報表 Excel"""
    xlsx_bytes = await service.export_inventory_report()
    filename = f"inventory_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/upload-photo")
async def upload_asset_photo(
    asset_id: int = Form(..., description="資產 ID"),
    file: UploadFile = File(..., description="資產照片"),
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """上傳資產照片"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="僅支援 JPEG/PNG/WebP/HEIC 格式")

    content = await file.read()
    if len(content) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail="檔案大小超過 10MB")

    asset = await service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="資產不存在")

    ASSET_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "photo.jpg").suffix.lower() or ".jpg"
    filename = f"asset_{asset_id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = ASSET_PHOTO_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    relative_path = f"uploads/asset_photos/{filename}"

    # Gemma 4 Vision 自動描述 (背景執行，不阻塞回應)
    ai_description = None
    try:
        import httpx, base64
        from app.services.ai.core.ai_config import get_ai_config
        config = get_ai_config()
        img_b64 = base64.b64encode(content).decode("ascii")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{config.ollama_base_url}/api/chat",
                json={
                    "model": config.ollama_model,
                    "messages": [{
                        "role": "user",
                        "content": "請用繁體中文簡短描述這張資產照片的內容（設備型號、外觀、狀態），30字以內。",
                        "images": [img_b64],
                    }],
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.2, "num_predict": 60},
                },
                timeout=30,
            )
            ai_description = resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.debug(f"Vision 描述失敗: {e}")

    from app.schemas.erp.asset import AssetUpdateRequest
    update_data = AssetUpdateRequest(id=asset_id, photo_path=relative_path)
    if ai_description and not asset.notes:
        update_data.notes = ai_description
    await service.update_asset(update_data, user_id=current_user.id)

    return SuccessResponse(
        data={"photo_path": relative_path, "ai_description": ai_description},
        message="照片上傳成功" + (f"（AI: {ai_description}）" if ai_description else ""),
    )


@router.post("/photo")
async def get_asset_photo(
    params: ERPIdRequest,
    service: AssetService = Depends(get_service(AssetService)),
    current_user: User = Depends(require_auth()),
):
    """取得資產照片"""
    asset = await service.get_asset(params.id)
    if not asset or not asset.photo_path:
        raise HTTPException(status_code=404, detail="照片不存在")

    file_path = Path(asset.photo_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="照片檔案遺失")

    return FileResponse(str(file_path))
