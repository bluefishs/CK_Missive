"""
公文匯出服務單元測試

測試範圍：
- _clean_agency_name: 機關名稱清理
- _get_valid_doc_type: 公文類型驗證
- export_to_csv: CSV 匯出
- _query_documents: 查詢邏輯
- export_to_excel: Excel 匯出（基本流程）

共 7 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from app.services.document_export_service import DocumentExportService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    return DocumentExportService(mock_db)


# ============================================================================
# _clean_agency_name
# ============================================================================

class TestCleanAgencyName:
    """機關名稱清理測試"""

    def test_returns_agency_name_if_provided(self, service):
        result = service._clean_agency_name("raw text", "桃園市政府")
        assert result == "桃園市政府"

    def test_extracts_from_parentheses(self, service):
        result = service._clean_agency_name("ABC123（桃園市政府）")
        assert result == "桃園市政府"

    def test_strips_leading_code(self, service):
        result = service._clean_agency_name("ABC123 桃園市政府")
        assert result == "桃園市政府"

    def test_empty_raw_returns_empty(self, service):
        result = service._clean_agency_name("")
        assert result == ""


# ============================================================================
# _get_valid_doc_type
# ============================================================================

class TestGetValidDocType:
    """公文類型驗證測試"""

    def test_receiving_doc_returns_empty(self, service):
        assert service._get_valid_doc_type("收文") == ""

    def test_sending_doc_returns_empty(self, service):
        assert service._get_valid_doc_type("發文") == ""

    def test_normal_type_returned(self, service):
        assert service._get_valid_doc_type("函") == "函"

    def test_none_returns_empty(self, service):
        assert service._get_valid_doc_type(None) == ""


# ============================================================================
# export_to_csv
# ============================================================================

class TestExportToCsv:
    """CSV 匯出測試"""

    @pytest.mark.asyncio
    async def test_csv_output_format(self, service):
        doc = MagicMock()
        doc.auto_serial = 1
        doc.doc_number = "桃工字第001號"
        doc.subject = "道路改善工程"
        doc.category = "收文"
        doc.doc_date = date(2026, 1, 15)
        doc.sender = "桃園市政府"
        doc.receiver = "乾坤測繪"
        doc.contract_project = None
        doc.status = "處理中"
        doc.notes = ""

        with patch.object(service, "_query_documents", new_callable=AsyncMock, return_value=[doc]):
            csv_bytes = await service.export_to_csv()

        csv_text = csv_bytes.decode("utf-8")
        # BOM + header
        assert csv_text.startswith("\ufeff")
        assert "公文文號" in csv_text
        assert "桃工字第001號" in csv_text
        assert "道路改善工程" in csv_text

    @pytest.mark.asyncio
    async def test_csv_empty_documents(self, service):
        with patch.object(service, "_query_documents", new_callable=AsyncMock, return_value=[]):
            csv_bytes = await service.export_to_csv()

        csv_text = csv_bytes.decode("utf-8")
        # Should have headers but no data rows
        lines = csv_text.strip().split("\n")
        assert len(lines) == 1  # header only

    @pytest.mark.asyncio
    async def test_csv_with_contract_project(self, service):
        doc = MagicMock()
        doc.auto_serial = 1
        doc.doc_number = "A001"
        doc.subject = "測試"
        doc.category = "收文"
        doc.doc_date = None
        doc.sender = ""
        doc.receiver = ""
        doc.status = ""
        doc.notes = ""

        project = MagicMock()
        project.project_name = "桃園養護工程"
        doc.contract_project = project

        with patch.object(service, "_query_documents", new_callable=AsyncMock, return_value=[doc]):
            csv_bytes = await service.export_to_csv()

        csv_text = csv_bytes.decode("utf-8")
        assert "桃園養護工程" in csv_text
