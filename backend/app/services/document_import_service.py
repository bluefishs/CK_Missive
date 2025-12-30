import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException # Import HTTPException for consistency

from app.services.csv_processor import DocumentCSVProcessor
from app.services.document_service import DocumentService
from app.schemas.document import DocumentImportResult # Assuming this schema is needed for return type

logger = logging.getLogger(__name__)

class DocumentImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.csv_processor = DocumentCSVProcessor()
        self.document_service = DocumentService(db)

    async def import_documents_from_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Orchestrates the entire document import process from a raw CSV file.
        """
        logger.info(f"DocumentImportService: Starting import for file: {filename}")

        # 1. Process CSV content using DocumentCSVProcessor
        try:
            logger.info(f"DocumentImportService: Starting CSV processing for {filename}, file size: {len(file_content)} bytes")
            processed_documents = self.csv_processor.process_csv_content(file_content, filename)
            logger.info(f"DocumentImportService: CSV processing completed. Found {len(processed_documents)} valid records.")
            if processed_documents:
                logger.info(f"DocumentImportService: First document keys: {list(processed_documents[0].keys())}")
        except Exception as e:
            logger.error(f"DocumentImportService: CSV processing failed for {filename}: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"CSV 檔案處理失敗: {str(e)}")

        if not processed_documents:
            logger.error(f"DocumentImportService: No valid documents found in {filename}!")
            raise HTTPException(status_code=400, detail="CSV 檔案中沒有有效的公文資料")

        # 2. Import processed documents into the database using DocumentService
        try:
            import_result: DocumentImportResult = await self.document_service.import_documents_from_processed_data(processed_documents)
            logger.info(f"DocumentImportService: Database import completed. Success: {import_result.success_count}, Error: {import_result.error_count}")
        except HTTPException:
            raise # Re-raise HTTPExceptions from document_service
        except Exception as e:
            logger.error(f"DocumentImportService: Database import failed for {filename}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"資料庫匯入失敗: {str(e)}")

        # 構建適當的返回消息
        if import_result.success_count == 0 and import_result.skipped_count > 0:
            message = f"CSV 檔案處理成功，但發現 {import_result.skipped_count} 筆重複記錄已跳過（資料庫中已存在相同公文字號）"
        elif import_result.success_count > 0:
            message = f"CSV 匯入完成：新增 {import_result.success_count} 筆，跳過重複 {import_result.skipped_count} 筆"
        else:
            message = "CSV 匯入完成，使用成熟的去重和流水號機制"

        return {
            "success": True,
            "message": message,
            "total_processed": import_result.total_rows,
            "success_count": import_result.success_count,
            "skipped_count": import_result.skipped_count,
            "error_count": import_result.error_count,
            "processor_used": "DocumentImportService (orchestrates DocumentCSVProcessor and DocumentService)"
        }
