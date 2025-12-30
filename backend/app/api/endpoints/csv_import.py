# -*- coding: utf-8 -*-
"""
CSV匯入API端點 (已重構)
"""
import logging
import os
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.document_service import DocumentService
from app.schemas.document import DocumentImportResult
from app.api.endpoints.auth import get_current_user
from app.extended.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload-and-import", response_model=DocumentImportResult, summary="上傳並匯入公文CSV檔案")
async def upload_and_import_csv(
    file: UploadFile = File(..., description="要上傳的CSV檔案"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    接收使用者上傳的 CSV 檔案，進行處理並將公文資料匯入資料庫。
    - 自動整合智慧型關聯 (機關、案件)
    - 逐行驗證，並回傳詳細的成功/失敗報告
    - 整個匯入過程是一個資料庫事務，確保資料的原子性
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="檔案格式不正確，僅支援 CSV 檔案。")

    try:
        # 使用 pandas 讀取上傳的檔案內容
        df = pd.read_csv(file.file, encoding='utf-8-sig', keep_default_na=False)
        # 將所有欄位名稱轉為小寫並替換空格，以匹配模型欄位
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        # 為了相容性，手動對應幾個常見的中文欄位名稱
        column_mapping = {
            '公文文號': 'doc_number', 
            '主旨': 'subject',
            '發文單位': 'sender',
            '受文單位': 'receiver',
            '發文日期': 'doc_date',
            '收文日期': 'receive_date',
            '承攬案件': 'contract_case'
        }
        df.rename(columns=column_mapping, inplace=True)

    except Exception as e:
        logger.error(f"讀取或解析CSV檔案失敗: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"無法讀取或解析CSV檔案: {e}")

    if df.empty:
        return DocumentImportResult(
            total_rows=0, success_count=0, error_count=0, skipped_count=0, 
            errors=["CSV檔案為空或格式不正確"]
        )

    # 初始化服務並執行匯入
    document_service = DocumentService(db)
    import_result = await document_service.import_documents(df, current_user_id=current_user.id)

    if import_result.error_count > 0:
        # 如果服務層回報有錯誤，我們回傳一個客戶端錯誤狀態碼
        raise HTTPException(status_code=422, detail=import_result.dict())

    return import_result
