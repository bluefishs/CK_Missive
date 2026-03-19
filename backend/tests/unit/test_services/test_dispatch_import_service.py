"""
派工單 Excel 匯入服務單元測試

測試範圍：
- _resolve_roc_year: 從承攬案件名稱解析民國年
- _link_documents_by_number: 根據文號建立派工-公文關聯
- _build_doc_number_map: 建立 doc_number → doc_id 映射
- import_from_excel: Excel 匯入主流程（欄位驗證/sheet偵測）
- generate_import_template: 匯入範本生成
- batch_relink_by_project: 批次重新關聯

共 8 test cases
"""

import io
import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pandas as pd

from app.services.taoyuan.dispatch_import_service import DispatchImportService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.get = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    with patch(
        "app.services.taoyuan.dispatch_import_service.DispatchOrderRepository"
    ), patch(
        "app.services.taoyuan.dispatch_import_service.DispatchDocLinkRepository"
    ):
        svc = DispatchImportService(mock_db)
        svc.repository = AsyncMock()
        svc.doc_link_repo = AsyncMock()
        return svc


# ============================================================================
# _resolve_roc_year
# ============================================================================

class TestResolveRocYear:
    """從承攬案件名稱解析民國年"""

    @pytest.mark.asyncio
    async def test_single_year(self, service, mock_db):
        """解析單一民國年格式 '115年度...'"""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = "115年度桃園市道路改善工程"
        mock_db.execute.return_value = result_mock

        year = await service._resolve_roc_year(1)
        assert year == 115

    @pytest.mark.asyncio
    async def test_range_year(self, service, mock_db):
        """解析年度範圍 '112至113年度...' 取起始年"""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = "112至113年度土地測量案"
        mock_db.execute.return_value = result_mock

        year = await service._resolve_roc_year(1)
        assert year == 112

    @pytest.mark.asyncio
    async def test_no_year_in_name(self, service, mock_db):
        """名稱中無年度時回傳當年民國年"""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = "道路拓寬工程"
        mock_db.execute.return_value = result_mock

        year = await service._resolve_roc_year(1)
        expected = datetime.now().year - 1911
        assert year == expected

    @pytest.mark.asyncio
    async def test_project_not_found(self, service, mock_db):
        """案件不存在時回傳當年民國年"""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        year = await service._resolve_roc_year(999)
        expected = datetime.now().year - 1911
        assert year == expected


# ============================================================================
# _link_documents_by_number
# ============================================================================

class TestLinkDocumentsByNumber:
    """根據文號建立派工-公文關聯"""

    @pytest.mark.asyncio
    async def test_link_agency_doc(self, service, mock_db):
        """機關文號成功關聯"""
        doc_number_map = {"桃工養字第1140001234號": 10}
        service.doc_link_repo.link_dispatch_to_document = AsyncMock(
            return_value=MagicMock()
        )
        mock_db.get.return_value = MagicMock(agency_doc_id=None, company_doc_id=None)

        with patch(
            "app.services.taoyuan.dispatch_import_service.parse_doc_numbers",
            return_value=["桃工養字第1140001234號"],
        ):
            result = await service._link_documents_by_number(
                dispatch_id=1,
                agency_raw="桃工養字第1140001234號",
                company_raw=None,
                doc_number_map=doc_number_map,
            )

        assert result["linked_count"] == 1
        assert result["agency_doc_id"] == 10
        assert result["not_found"] == []

    @pytest.mark.asyncio
    async def test_link_not_found(self, service, mock_db):
        """文號不在 map 中時記入 not_found"""
        doc_number_map = {}

        with patch(
            "app.services.taoyuan.dispatch_import_service.parse_doc_numbers",
            return_value=["不存在的文號"],
        ):
            result = await service._link_documents_by_number(
                dispatch_id=1,
                agency_raw="不存在的文號",
                company_raw=None,
                doc_number_map=doc_number_map,
            )

        assert result["linked_count"] == 0
        assert "不存在的文號" in result["not_found"]


# ============================================================================
# generate_import_template
# ============================================================================

class TestGenerateImportTemplate:
    """匯入範本生成"""

    def test_template_is_valid_excel(self, service):
        """生成的範本為有效 Excel 檔案"""
        result = service.generate_import_template()
        assert isinstance(result, bytes)
        assert len(result) > 0

        # 可成功讀取為 DataFrame
        df = pd.read_excel(io.BytesIO(result))
        assert "派工單號" in df.columns
        assert "工程名稱/派工事項" in df.columns
        assert len(df) == 1  # 含一行範例資料


# ============================================================================
# import_from_excel - validation
# ============================================================================

class TestImportFromExcelValidation:
    """Excel 匯入欄位驗證"""

    @pytest.mark.asyncio
    async def test_missing_required_columns(self, service):
        """欄位不足時回傳錯誤"""
        df = pd.DataFrame({"不相關欄位": ["test"]})
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        result = await service.import_from_excel(
            file_content=output.getvalue(),
            contract_project_id=1,
        )

        assert result["success"] is False
        assert result["error_count"] >= 1
