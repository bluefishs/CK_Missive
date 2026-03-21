"""費用報銷發票模組 — 單元測試

測試範圍：
- Schema 驗證 (發票號碼格式、統編格式、金額)
- QR 解析邏輯
- Service 業務邏輯 (重複檢查、審核入帳)
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.erp.expense import (
    ExpenseInvoiceCreate,
    ExpenseInvoiceUpdate,
    ExpenseInvoiceQuery,
    ExpenseInvoiceItemCreate,
)
from app.schemas.erp.ledger import LedgerCreate, LedgerQuery
from app.schemas.erp.financial_summary import (
    ProjectFinancialSummary,
    CompanyOverviewRequest,
    ProjectSummaryRequest,
)


# ============================================================================
# Schema 驗證測試
# ============================================================================

class TestExpenseInvoiceCreateSchema:
    """ExpenseInvoiceCreate Schema 驗證"""

    def test_valid_invoice(self):
        """正確格式的發票"""
        data = ExpenseInvoiceCreate(
            inv_num="AB12345678",
            date=date(2026, 3, 21),
            amount=Decimal("1050.00"),
            source="qr_scan",
        )
        assert data.inv_num == "AB12345678"
        assert data.amount == Decimal("1050.00")
        assert data.source == "qr_scan"

    def test_invalid_inv_num_format(self):
        """無效的發票號碼格式"""
        with pytest.raises(Exception):
            ExpenseInvoiceCreate(
                inv_num="12345",
                date=date(2026, 3, 21),
                amount=Decimal("100"),
            )

    def test_invalid_inv_num_lowercase(self):
        """小寫字母發票號碼"""
        with pytest.raises(Exception):
            ExpenseInvoiceCreate(
                inv_num="ab12345678",
                date=date(2026, 3, 21),
                amount=Decimal("100"),
            )

    def test_invalid_buyer_ban(self):
        """無效的統編格式"""
        with pytest.raises(Exception):
            ExpenseInvoiceCreate(
                inv_num="AB12345678",
                date=date(2026, 3, 21),
                amount=Decimal("100"),
                buyer_ban="123",
            )

    def test_valid_ban(self):
        """正確的統編"""
        data = ExpenseInvoiceCreate(
            inv_num="AB12345678",
            date=date(2026, 3, 21),
            amount=Decimal("100"),
            buyer_ban="12345678",
            seller_ban="87654321",
        )
        assert data.buyer_ban == "12345678"
        assert data.seller_ban == "87654321"

    def test_amount_must_be_positive(self):
        """金額必須大於零"""
        with pytest.raises(Exception):
            ExpenseInvoiceCreate(
                inv_num="AB12345678",
                date=date(2026, 3, 21),
                amount=Decimal("0"),
            )

    def test_optional_case_code(self):
        """case_code 可為 None (一般營運支出)"""
        data = ExpenseInvoiceCreate(
            inv_num="AB12345678",
            date=date(2026, 3, 21),
            amount=Decimal("100"),
            case_code=None,
        )
        assert data.case_code is None

    def test_with_items(self):
        """含品名明細"""
        item = ExpenseInvoiceItemCreate(
            item_name="文具", qty=Decimal("2"), unit_price=Decimal("50"), amount=Decimal("100")
        )
        data = ExpenseInvoiceCreate(
            inv_num="AB12345678",
            date=date(2026, 3, 21),
            amount=Decimal("100"),
            items=[item],
        )
        assert len(data.items) == 1
        assert data.items[0].item_name == "文具"

    def test_source_literals(self):
        """source 只接受指定值"""
        for src in ["qr_scan", "manual", "api", "ocr"]:
            data = ExpenseInvoiceCreate(
                inv_num="AB12345678",
                date=date(2026, 3, 21),
                amount=Decimal("100"),
                source=src,
            )
            assert data.source == src

    def test_invalid_source(self):
        """無效的 source 值"""
        with pytest.raises(Exception):
            ExpenseInvoiceCreate(
                inv_num="AB12345678",
                date=date(2026, 3, 21),
                amount=Decimal("100"),
                source="invalid",
            )


class TestLedgerCreateSchema:
    """LedgerCreate Schema 驗證"""

    def test_valid_income(self):
        data = LedgerCreate(
            amount=Decimal("5000"),
            entry_type="income",
            category="收款",
            case_code="P113-001",
        )
        assert data.entry_type == "income"

    def test_valid_expense(self):
        data = LedgerCreate(
            amount=Decimal("1200"),
            entry_type="expense",
            category="交通",
        )
        assert data.entry_type == "expense"
        assert data.case_code is None

    def test_invalid_entry_type(self):
        with pytest.raises(Exception):
            LedgerCreate(
                amount=Decimal("100"),
                entry_type="transfer",
            )

    def test_amount_must_be_positive(self):
        with pytest.raises(Exception):
            LedgerCreate(amount=Decimal("-100"), entry_type="expense")


class TestFinancialSummarySchemas:
    """財務彙總 Schema 驗證"""

    def test_project_summary_defaults(self):
        summary = ProjectFinancialSummary(case_code="P113-001")
        assert summary.billed_amount == Decimal("0")
        assert summary.net_balance == Decimal("0")
        assert summary.budget_alert is None

    def test_company_overview_request(self):
        req = CompanyOverviewRequest(year=113, top_n=5)
        assert req.year == 113
        assert req.top_n == 5

    def test_project_summary_request(self):
        req = ProjectSummaryRequest(case_code="P113-001")
        assert req.case_code == "P113-001"


# ============================================================================
# QR 解析測試
# ============================================================================

class TestQRParsing:
    """QR Code 解析邏輯測試"""

    @pytest.fixture
    def service(self):
        from app.services.expense_invoice_service import ExpenseInvoiceService
        mock_db = AsyncMock()
        return ExpenseInvoiceService(mock_db)

    def test_parse_valid_qr(self, service):
        """解析有效 QR 資料"""
        # 模擬 QR: 發票號碼(10) + 日期(7) + 填充(8) + 買方(8) + 賣方(8) + 金額hex(8) + padding
        qr = "AB12345678" + "1150321" + "ABCD1234" + "12345678" + "87654321" + "00000420" + "0" * 30
        result = service.parse_qr_data(qr)
        assert result["inv_num"] == "AB12345678"
        assert result["buyer_ban"] == "12345678"
        assert result["seller_ban"] == "87654321"
        assert result["amount"] == Decimal("1056")  # 0x420 = 1056
        assert result["source"] == "qr_scan"

    def test_parse_qr_date_conversion(self, service):
        """民國日期轉西元"""
        qr = "CD99887766" + "1150101" + "AAAA1111" + "11111111" + "22222222" + "00000064" + "0" * 30
        result = service.parse_qr_data(qr)
        assert result["date"] == date(2026, 1, 1)  # 民國115年 = 西元2026年

    def test_parse_short_qr_raises(self, service):
        """過短的 QR 資料"""
        with pytest.raises(ValueError, match="QR 資料格式不正確"):
            service.parse_qr_data("AB123")

    def test_parse_empty_qr_raises(self, service):
        """空 QR 資料"""
        with pytest.raises(ValueError, match="QR 資料格式不正確"):
            service.parse_qr_data("")


# ============================================================================
# Service 業務邏輯測試
# ============================================================================

class TestExpenseInvoiceService:
    """ExpenseInvoiceService 業務邏輯"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.expense_invoice_service import ExpenseInvoiceService
        svc = ExpenseInvoiceService(mock_db)
        svc.repo = AsyncMock()
        svc.ledger_repo = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_create_duplicate_raises(self, service):
        """重複發票號碼應拋出錯誤"""
        service.repo.check_duplicate = AsyncMock(return_value=True)
        data = ExpenseInvoiceCreate(
            inv_num="AB12345678",
            date=date(2026, 3, 21),
            amount=Decimal("100"),
        )
        with pytest.raises(ValueError, match="已存在"):
            await service.create(data)

    @pytest.mark.asyncio
    async def test_approve_auto_ledger(self, service, mock_db):
        """審核通過時自動建立帳本記錄"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.status = "pending"
        mock_invoice.case_code = "P113-001"
        mock_invoice.amount = Decimal("500")
        mock_invoice.category = "交通"
        mock_invoice.inv_num = "AB12345678"
        mock_invoice.user_id = 1
        mock_invoice.date = date(2026, 3, 21)

        service.repo.get_by_id = AsyncMock(return_value=mock_invoice)

        await service.approve(1)

        assert mock_invoice.status == "verified"
        mock_db.add.assert_called_once()  # FinanceLedger 被加入 session

    @pytest.mark.asyncio
    async def test_approve_already_verified_raises(self, service):
        """已審核的發票不可再次審核"""
        mock_invoice = MagicMock()
        mock_invoice.status = "verified"
        service.repo.get_by_id = AsyncMock(return_value=mock_invoice)

        with pytest.raises(ValueError, match="已審核通過"):
            await service.approve(1)

    @pytest.mark.asyncio
    async def test_reject_with_reason(self, service):
        """駁回帶原因"""
        mock_invoice = MagicMock()
        mock_invoice.status = "pending"
        mock_invoice.notes = None
        service.repo.get_by_id = AsyncMock(return_value=mock_invoice)

        await service.reject(1, reason="金額有誤")

        assert mock_invoice.status == "rejected"
        assert "金額有誤" in mock_invoice.notes

    @pytest.mark.asyncio
    async def test_reject_verified_raises(self, service):
        """已審核通過的不可駁回"""
        mock_invoice = MagicMock()
        mock_invoice.status = "verified"
        service.repo.get_by_id = AsyncMock(return_value=mock_invoice)

        with pytest.raises(ValueError, match="已審核通過"):
            await service.reject(1)


class TestFinanceLedgerService:
    """FinanceLedgerService 業務邏輯"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.finance_ledger_service import FinanceLedgerService
        svc = FinanceLedgerService(mock_db)
        svc.repo = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_delete_manual_ok(self, service, mock_db):
        """手動記帳可刪除"""
        mock_ledger = MagicMock()
        mock_ledger.source_type = "manual"
        service.repo.get_by_id = AsyncMock(return_value=mock_ledger)

        result = await service.delete(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_auto_raises(self, service):
        """系統自動入帳不可刪除"""
        mock_ledger = MagicMock()
        mock_ledger.source_type = "expense_invoice"
        service.repo.get_by_id = AsyncMock(return_value=mock_ledger)

        with pytest.raises(ValueError, match="僅可刪除手動記帳"):
            await service.delete(1)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service):
        """不存在的記錄"""
        service.repo.get_by_id = AsyncMock(return_value=None)
        result = await service.delete(999)
        assert result is False


class TestExpenseInvoiceQuery:
    """查詢 Schema 測試"""

    def test_default_pagination(self):
        q = ExpenseInvoiceQuery()
        assert q.skip == 0
        assert q.limit == 20

    def test_filter_by_case_code(self):
        q = ExpenseInvoiceQuery(case_code="P113-001")
        assert q.case_code == "P113-001"

    def test_limit_max(self):
        with pytest.raises(Exception):
            ExpenseInvoiceQuery(limit=200)

    def test_ledger_query_defaults(self):
        q = LedgerQuery()
        assert q.skip == 0
        assert q.limit == 20
        assert q.entry_type is None
