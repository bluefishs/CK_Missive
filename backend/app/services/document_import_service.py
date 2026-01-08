# -*- coding: utf-8 -*-
"""
CSV 公文匯入服務

整合 DocumentCSVProcessor 處理 CSV 解析，
並使用 DocumentService 寫入資料庫。
繼承 ImportBaseService 以使用統一的驗證與回應機制。

版本: 2.0.0
更新: 2026-01-08 - 重構繼承 ImportBaseService
"""
import logging
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.services.base.import_base import ImportBaseService
from app.services.base.response import ImportResult, ImportRowResult
from app.services.csv_processor import DocumentCSVProcessor
from app.services.document_service import DocumentService
from app.schemas.document import DocumentImportResult

logger = logging.getLogger(__name__)


class DocumentImportService(ImportBaseService):
    """
    CSV 公文匯入服務

    作為協調器服務，整合 CSV 處理與資料庫匯入。
    繼承 ImportBaseService 以使用共用的驗證邏輯與回應結構。
    """

    def __init__(self, db: AsyncSession):
        """
        初始化 CSV 匯入服務

        Args:
            db: 資料庫連線
        """
        super().__init__(db)
        self.csv_processor = DocumentCSVProcessor()
        self.document_service = DocumentService(db)

    async def import_from_file(
        self,
        file_content: bytes,
        filename: str
    ) -> ImportResult:
        """
        從 CSV 檔案匯入公文資料

        實作 ImportBaseService 的抽象方法。

        Args:
            file_content: CSV 檔案內容
            filename: 檔案名稱

        Returns:
            ImportResult: 統一的匯入結果
        """
        logger.info(f"DocumentImportService: 開始處理檔案: {filename}")

        # 重置流水號計數器（每次匯入批次獨立）
        self.reset_serial_counters()

        errors: List[ImportRowResult] = []
        warnings: List[ImportRowResult] = []

        # 1. 使用 DocumentCSVProcessor 處理 CSV 內容
        try:
            logger.info(f"DocumentImportService: 開始 CSV 處理, 檔案大小: {len(file_content)} bytes")
            processed_documents = self.csv_processor.process_csv_content(file_content, filename)
            logger.info(f"DocumentImportService: CSV 處理完成, 找到 {len(processed_documents)} 筆有效記錄")

            if processed_documents:
                logger.debug(f"DocumentImportService: 第一筆欄位: {list(processed_documents[0].keys())}")
                for i, doc in enumerate(processed_documents[:3]):
                    logger.debug(f"DocumentImportService: Doc[{i}] doc_number='{doc.get('doc_number', '')}'")

        except Exception as e:
            logger.error(f"DocumentImportService: CSV 處理失敗: {e}", exc_info=True)
            return ImportResult(
                success=False,
                filename=filename,
                total_rows=0,
                errors=[ImportRowResult(
                    row=0,
                    status='error',
                    message=f"CSV 檔案處理失敗: {str(e)}"
                )]
            )

        if not processed_documents:
            logger.warning(f"DocumentImportService: 檔案 {filename} 中沒有有效公文資料")
            return ImportResult(
                success=False,
                filename=filename,
                total_rows=0,
                errors=[ImportRowResult(
                    row=0,
                    status='error',
                    message="CSV 檔案中沒有有效的公文資料"
                )]
            )

        # 2. 使用 DocumentService 匯入至資料庫
        try:
            db_result: DocumentImportResult = await self.document_service.import_documents_from_processed_data(
                processed_documents
            )
            logger.info(
                f"DocumentImportService: 資料庫匯入完成. "
                f"成功: {db_result.success_count}, 跳過: {db_result.skipped_count}, 錯誤: {db_result.error_count}"
            )

            # 轉換錯誤格式
            if db_result.errors:
                for err in db_result.errors:
                    if isinstance(err, dict):
                        errors.append(ImportRowResult(
                            row=err.get('row', 0),
                            status='error',
                            message=err.get('error', str(err)),
                            doc_number=err.get('doc_number', '')
                        ))
                    else:
                        errors.append(ImportRowResult(
                            row=0,
                            status='error',
                            message=str(err)
                        ))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"DocumentImportService: 資料庫匯入失敗: {e}", exc_info=True)
            return ImportResult(
                success=False,
                filename=filename,
                total_rows=len(processed_documents),
                errors=[ImportRowResult(
                    row=0,
                    status='error',
                    message=f"資料庫匯入失敗: {str(e)}"
                )]
            )

        # 3. 構建 ImportResult
        success = db_result.success_count > 0 or (db_result.error_count == 0 and db_result.skipped_count > 0)

        return ImportResult(
            success=success,
            filename=filename,
            total_rows=db_result.total_rows,
            inserted=db_result.success_count,
            updated=0,  # CSV 匯入目前不支援更新
            skipped=db_result.skipped_count,
            errors=errors,
            warnings=warnings
        )

    async def process_row(
        self,
        row_num: int,
        row_data: Dict[str, Any]
    ) -> ImportRowResult:
        """
        處理單列 CSV 資料

        此方法委派給 DocumentCSVProcessor.process_row() 處理。

        Args:
            row_num: 列號
            row_data: 列資料

        Returns:
            ImportRowResult: 處理結果
        """
        try:
            processed = self.csv_processor.process_row(row_data)
            if processed:
                return ImportRowResult(
                    row=row_num,
                    status='processed',
                    message='資料處理成功',
                    doc_number=processed.get('doc_number', '')
                )
            else:
                return ImportRowResult(
                    row=row_num,
                    status='skipped',
                    message='資料驗證失敗或不完整'
                )
        except Exception as e:
            return ImportRowResult(
                row=row_num,
                status='error',
                message=str(e)
            )

    # ========== 相容性方法 ==========

    async def import_documents_from_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        從 CSV 檔案匯入公文（相容舊版 API）

        維持原有回傳格式以確保向後相容。

        Args:
            file_content: 檔案內容
            filename: 檔案名稱

        Returns:
            Dict: 相容舊版的回應格式
        """
        # 呼叫新的 import_from_file 方法
        result = await self.import_from_file(file_content, filename)

        # 構建相容舊版的訊息
        if result.inserted == 0 and result.skipped > 0:
            message = f"CSV 檔案處理成功，但發現 {result.skipped} 筆重複記錄已跳過（資料庫中已存在相同公文字號）"
        elif result.inserted > 0:
            message = f"CSV 匯入完成：新增 {result.inserted} 筆，跳過重複 {result.skipped} 筆"
        else:
            message = "CSV 匯入完成，使用成熟的去重和流水號機制"

        # 轉換錯誤格式
        errors_list = []
        for err in result.errors:
            errors_list.append({
                'row': err.row,
                'error': err.message,
                'doc_number': err.doc_number
            })

        return {
            "success": result.success,
            "message": message,
            "total_processed": result.total_rows,
            "success_count": result.inserted,
            "skipped_count": result.skipped,
            "error_count": len(result.errors),
            "errors": errors_list,
            "processor_used": "DocumentImportService (ImportBaseService)"
        }
