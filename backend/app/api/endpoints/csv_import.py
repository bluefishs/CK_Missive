# -*- coding: utf-8 -*-
"""
CSV匯入API端點 (使用 DocumentImportService 完整處理)
支援單檔及多檔批次上傳
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.document_import_service import DocumentImportService
from app.api.endpoints.auth import get_current_user
from app.extended.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload-and-import", summary="上傳並匯入公文CSV檔案")
async def upload_and_import_csv(
    file: UploadFile = File(..., description="要上傳的CSV檔案"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    接收使用者上傳的 CSV 檔案，進行處理並將公文資料匯入資料庫。
    - 自動偵測 CSV 標頭行（支援前幾行為說明資訊的格式）
    - 自動整合智慧型關聯 (機關、案件)
    - 組合公文字號（格式：{字}字第{文號}號）
    - 逐行驗證，並回傳詳細的成功/失敗報告
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="檔案格式不正確，僅支援 CSV 檔案。")

    try:
        # 讀取檔案內容
        file_content = await file.read()
        filename = file.filename

        logger.info(f"開始處理 CSV 匯入: {filename}, 大小: {len(file_content)} bytes")

        # 使用 DocumentImportService 處理（包含 CSV 標頭偵測和資料轉換）
        import_service = DocumentImportService(db)
        result = await import_service.import_documents_from_file(file_content, filename)

        logger.info(f"CSV 匯入完成: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV匯入失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"CSV匯入失敗: {str(e)}")


@router.post("/upload-multiple", summary="批次上傳多個CSV檔案")
async def upload_multiple_csv(
    files: List[UploadFile] = File(..., description="要上傳的多個CSV檔案"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    批次上傳多個 CSV 檔案，依序處理並匯入資料庫。
    回傳每個檔案的處理結果彙總。
    """
    if not files:
        raise HTTPException(status_code=400, detail="請至少上傳一個檔案")

    results = []
    total_success = 0
    total_skipped = 0
    total_errors = 0
    total_processed = 0

    import_service = DocumentImportService(db)

    for file in files:
        file_result = {
            "filename": file.filename,
            "success": False,
            "message": "",
            "success_count": 0,
            "skipped_count": 0,
            "error_count": 0
        }

        # 驗證檔案格式
        if not file.filename or not file.filename.endswith('.csv'):
            file_result["message"] = "檔案格式不正確，僅支援 CSV 檔案"
            results.append(file_result)
            continue

        try:
            file_content = await file.read()
            logger.info(f"批次匯入 - 處理檔案: {file.filename}, 大小: {len(file_content)} bytes")

            result = await import_service.import_documents_from_file(file_content, file.filename)

            file_result["success"] = True
            file_result["message"] = result.get("message", "匯入完成")
            file_result["success_count"] = result.get("success_count", 0)
            file_result["skipped_count"] = result.get("skipped_count", 0)
            file_result["error_count"] = result.get("error_count", 0)
            file_result["total_processed"] = result.get("total_processed", 0)

            total_success += file_result["success_count"]
            total_skipped += file_result["skipped_count"]
            total_errors += file_result["error_count"]
            total_processed += file_result.get("total_processed", 0)

        except HTTPException as e:
            file_result["message"] = e.detail
            file_result["error_count"] = 1
            total_errors += 1
        except Exception as e:
            logger.error(f"批次匯入 - 檔案 {file.filename} 處理失敗: {e}", exc_info=True)
            file_result["message"] = f"處理失敗: {str(e)}"
            file_result["error_count"] = 1
            total_errors += 1

        results.append(file_result)

    return {
        "success": True,
        "message": f"批次匯入完成：共處理 {len(files)} 個檔案",
        "summary": {
            "files_count": len(files),
            "total_processed": total_processed,
            "total_success": total_success,
            "total_skipped": total_skipped,
            "total_errors": total_errors
        },
        "file_results": results
    }
