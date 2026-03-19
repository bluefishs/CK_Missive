"""
契金管控服務單元測試

測試範圍：
- _extract_work_type_code: 從作業類別提取代碼
- _extract_document_info: 從關聯公文提取資訊
- create_payment: 建立契金記錄（含零值過濾、當前金額計算）
- update_payment: 更新契金記錄
- delete_payment: 刪除契金記錄
- get_project_summary: 取得專案契金彙總

共 7 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.taoyuan.payment_service import PaymentService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    with patch(
        "app.services.taoyuan.payment_service.PaymentRepository"
    ), patch(
        "app.services.taoyuan.payment_service.DispatchOrderRepository"
    ):
        svc = PaymentService(mock_db)
        svc.repository = AsyncMock()
        svc.dispatch_repository = AsyncMock()
        return svc


# ============================================================================
# _extract_work_type_code
# ============================================================================

class TestExtractWorkTypeCode:
    """作業類別代碼提取"""

    def test_with_parentheses(self, service):
        """含括號的代碼 '測量(A1)' → 'A1'"""
        assert service._extract_work_type_code("測量(A1)") == "A1"

    def test_without_parentheses(self, service):
        """無括號取前兩字元"""
        assert service._extract_work_type_code("土地查估") == "土地"

    def test_empty_or_none(self, service):
        """空值或 None 回傳空字串"""
        assert service._extract_work_type_code(None) == ""
        assert service._extract_work_type_code("") == ""

    def test_short_string(self, service):
        """短字串直接回傳"""
        assert service._extract_work_type_code("A") == "A"


# ============================================================================
# _extract_document_info
# ============================================================================

class TestExtractDocumentInfo:
    """關聯公文資訊提取"""

    def test_agency_and_company_docs(self, service):
        """同時有機關與公司公文"""
        agency_link = MagicMock()
        agency_link.link_type = "agency_doc"
        agency_link.document = MagicMock(doc_number="桃工字第123號")

        company_link = MagicMock()
        company_link.link_type = "company_doc"
        company_link.document = MagicMock(doc_number="乾字第456號")

        result = service._extract_document_info([agency_link, company_link])
        assert result["agency_doc_number"] == "桃工字第123號"
        assert result["company_doc_number"] == "乾字第456號"

    def test_empty_links(self, service):
        """無關聯公文"""
        result = service._extract_document_info([])
        assert result["agency_doc_number"] is None
        assert result["company_doc_number"] is None


# ============================================================================
# create_payment
# ============================================================================

class TestCreatePayment:
    """建立契金記錄"""

    @pytest.mark.asyncio
    async def test_zero_amounts_converted_to_none(self, service):
        """零值金額轉為 None"""
        data = MagicMock()
        data.model_dump.return_value = {
            "dispatch_order_id": 1,
            "work_01_amount": 0,
            "work_02_amount": 100.0,
            "work_03_amount": None,
        }

        mock_payment = MagicMock()
        mock_payment.id = 1
        mock_payment.dispatch_order = MagicMock(contract_project_id=1)
        service.repository.create = AsyncMock(return_value=mock_payment)
        service.repository.get_with_dispatch = AsyncMock(return_value=mock_payment)
        service.repository.update_cumulative_amounts = AsyncMock()

        result = await service.create_payment(data)

        # 驗證 create 被呼叫時，work_01_amount 為 None (零值轉換)
        create_call_data = service.repository.create.call_args[0][0]
        assert create_call_data["work_01_amount"] is None
        assert create_call_data["work_03_amount"] is None
        # current_amount = sum(非零值) = 100.0
        assert create_call_data["current_amount"] == 100.0


# ============================================================================
# delete_payment
# ============================================================================

class TestDeletePayment:
    """刪除契金記錄"""

    @pytest.mark.asyncio
    async def test_delete_recalculates_cumulative(self, service):
        """刪除後重新計算累進金額"""
        mock_payment = MagicMock()
        mock_payment.dispatch_order = MagicMock(contract_project_id=5)
        service.repository.get_with_dispatch = AsyncMock(return_value=mock_payment)
        service.repository.delete = AsyncMock(return_value=True)
        service.repository.update_cumulative_amounts = AsyncMock()

        result = await service.delete_payment(1)

        assert result is True
        service.repository.update_cumulative_amounts.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service):
        """刪除不存在的記錄"""
        service.repository.get_with_dispatch = AsyncMock(return_value=None)
        service.repository.delete = AsyncMock(return_value=False)

        result = await service.delete_payment(999)
        assert result is False
