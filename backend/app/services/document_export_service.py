# -*- coding: utf-8 -*-
"""
公文匯出服務

處理將公文資料匯出為 Excel 檔案的邏輯。
"""
import pandas as pd
from io import BytesIO
from typing import Any, Dict, List
from app.services.document_service import DocumentService
import logging

logger = logging.getLogger(__name__)


class DocumentExportService:
    """
    服務層：處理將公文資料匯出為 Excel 檔案的邏輯
    """

    def __init__(self, document_service: DocumentService) -> None:
        """
        初始化匯出服務

        Args:
            document_service: 公文服務實例
        """
        self.document_service: DocumentService = document_service

    async def export_documents_to_excel(self, document_ids: List[int]) -> bytes:
        """
        根據提供的公文 ID 列表，查詢資料並生成 Excel 檔案。

        Args:
            document_ids: 要匯出的公文 ID 列表。

        Returns:
            包含 Excel 檔案內容的 bytes。
        """
        logger.info(f"開始匯出 {len(document_ids)} 筆公文資料...")

        # 1. 從資料庫獲取公文資料
        documents = await self.document_service.get_documents_by_ids(document_ids)
        if not documents:
            logger.warning("找不到任何符合條件的公文可供匯出。")
            return b""

        # 2. 將資料轉換為字典列表 (支援 Pydantic v1/v2)
        data_to_export: List[Dict[str, Any]] = [
            doc.model_dump() if hasattr(doc, 'model_dump') else doc.dict()
            for doc in documents
        ]
        
        # 3. 使用 pandas 創建 DataFrame
        df = pd.DataFrame(data_to_export)

        # 4. 調整欄位順序與名稱 (使其更符合使用者習慣)
        column_mapping = {
            "id": "系統編號",
            "auto_serial": "流水號",
            "doc_type": "文件類型",
            "doc_number": "公文字號",
            "doc_date": "公文日期",
            "subject": "主旨",
            "sender": "發文機關",
            "receiver": "收文機關",
            "status": "辦理情形",
            "receive_date": "收文日期",
            "send_date": "發文日期",
            "doc_word": "字",
            "doc_class": "類別",
            "priority_level": "速別",
            "notes": "備註",
            "contract_case": "承攬案件",
            "created_at": "建立時間",
            "updated_at": "更新時間",
        }
        
        # 重新命名 df 中存在的欄位
        df_renamed = df.rename(columns=column_mapping)

        # 取得重新命名後的欄位列表 (依照 column_mapping 的順序)
        final_columns = [column_mapping[col] for col in column_mapping if column_mapping[col] in df_renamed.columns]
        
        # 只選擇要匯出的欄位
        df_final = df_renamed[final_columns]

        # 5. 創建一個記憶體中的 Excel 檔案
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='公文清單')
        
        excel_data = output.getvalue()
        logger.info(f"成功生成 Excel 檔案，大小為 {len(excel_data)} bytes。")

        return excel_data
