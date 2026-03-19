"""
公文匯入服務單元測試

測試範圍：
- import_from_file: CSV 匯入主流程
- process_row: 單列處理
- import_documents_from_file: 相容舊版 API
- 異常處理與邊界條件

共 8 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.document_import_service import DocumentImportService
from app.services.base.response import ImportResult, ImportRowResult
from app.schemas.document import DocumentImportResult


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    with patch.object(DocumentImportService, "__init__", lambda self, db: None):
        svc = DocumentImportService.__new__(DocumentImportService)
        svc.db = mock_db
        svc.csv_processor = MagicMock()
        svc.document_service = AsyncMock()
        svc._serial_counters = {}
        return svc


# ============================================================================
# import_from_file
# ============================================================================

class TestImportFromFile:
    """CSV 匯入主流程測試"""

    @pytest.mark.asyncio
    async def test_successful_import(self, service):
        service.csv_processor.process_csv_content.return_value = [
            {"doc_number": "A001", "subject": "測試"},
            {"doc_number": "A002", "subject": "測試2"},
        ]
        service.reset_serial_counters = MagicMock()

        db_result = DocumentImportResult(
            total_rows=2, success_count=2, skipped_count=0,
            error_count=0, errors=[], processing_time=0.5
        )
        service.document_service.import_documents_from_processed_data = AsyncMock(return_value=db_result)

        result = await service.import_from_file(b"csv content", "test.csv")
        assert result.success is True
        assert result.inserted == 2
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_empty_csv_returns_error(self, service):
        service.csv_processor.process_csv_content.return_value = []
        service.reset_serial_counters = MagicMock()

        result = await service.import_from_file(b"empty", "test.csv")
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_csv_processing_exception(self, service):
        service.csv_processor.process_csv_content.side_effect = Exception("Parse error")
        service.reset_serial_counters = MagicMock()

        result = await service.import_from_file(b"bad data", "test.csv")
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_db_import_exception(self, service):
        service.csv_processor.process_csv_content.return_value = [
            {"doc_number": "A001", "subject": "測試"},
        ]
        service.reset_serial_counters = MagicMock()
        service.document_service.import_documents_from_processed_data = AsyncMock(
            side_effect=Exception("DB error")
        )

        result = await service.import_from_file(b"csv data", "test.csv")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_all_skipped_still_success(self, service):
        service.csv_processor.process_csv_content.return_value = [
            {"doc_number": "A001"},
        ]
        service.reset_serial_counters = MagicMock()

        db_result = DocumentImportResult(
            total_rows=1, success_count=0, skipped_count=1,
            error_count=0, errors=[], processing_time=0.1
        )
        service.document_service.import_documents_from_processed_data = AsyncMock(return_value=db_result)

        result = await service.import_from_file(b"csv", "test.csv")
        assert result.success is True
        assert result.skipped == 1


# ============================================================================
# process_row
# ============================================================================

class TestProcessRow:
    """單列處理測試"""

    @pytest.mark.asyncio
    async def test_process_row_success(self, service):
        service.csv_processor.process_row.return_value = {"doc_number": "A001"}
        result = await service.process_row(1, {"doc_number": "A001"})
        assert result.status == "processed"

    @pytest.mark.asyncio
    async def test_process_row_skipped(self, service):
        service.csv_processor.process_row.return_value = None
        result = await service.process_row(1, {})
        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_process_row_exception(self, service):
        service.csv_processor.process_row.side_effect = Exception("bad data")
        result = await service.process_row(1, {"bad": "data"})
        assert result.status == "error"
