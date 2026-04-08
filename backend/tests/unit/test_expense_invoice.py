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
        # 模擬 QR: 發票號碼(10) + 日期(7) + 隨機碼(4) + 銷售額hex(8) + 總額hex(8) + 買方統編(8) + 賣方統編(8) + 驗證碼(24)
        qr = "AB12345678" + "1150321" + "ABCD" + "00000000" + "00000420" + "12345678" + "87654321" + "0" * 24
        result = service.parse_qr_data(qr)
        assert result["inv_num"] == "AB12345678"
        assert result["buyer_ban"] == "12345678"
        assert result["seller_ban"] == "87654321"
        assert result["amount"] == Decimal("1056")  # 0x420 = 1056
        assert result["source"] == "qr_scan"

    def test_parse_qr_date_conversion(self, service):
        """民國日期轉西元"""
        # 格式: 發票號碼(10) + 日期(7) + 隨機碼(4) + 銷售額hex(8) + 總額hex(8) + 買方統編(8) + 賣方統編(8) + 驗證碼(24)
        qr = "CD99887766" + "1150101" + "AAAA" + "00000000" + "00000064" + "11111111" + "22222222" + "0" * 24
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

    @pytest.fixture
    def approval_service(self, mock_db):
        """Direct access to ExpenseApprovalService for approve/reject tests"""
        from app.services.expense_approval_service import ExpenseApprovalService
        svc = ExpenseApprovalService(mock_db)
        svc.repo = AsyncMock()
        svc.ledger_service = AsyncMock()
        svc.ledger_service.find_by_source = AsyncMock(return_value=None)
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
    async def test_approve_pending_to_manager(self, approval_service, mock_db):
        """pending → manager_approved (第一層)"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.status = "pending"
        mock_invoice.amount = Decimal("500")

        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        approval_service.repo.update_status = AsyncMock(return_value=mock_invoice)
        approval_service.repo.commit = AsyncMock()

        await approval_service.approve(1)

        approval_service.repo.update_status.assert_called_once_with(mock_invoice, "manager_approved")
        approval_service.ledger_service.record_from_expense.assert_not_called()

    @pytest.mark.asyncio
    async def test_approve_low_value_manager_to_verified(self, approval_service, mock_db):
        """≤30K: manager_approved → verified + 入帳"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.status = "manager_approved"
        mock_invoice.amount = Decimal("25000")
        mock_invoice.case_code = None  # 略過預算檢查

        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        approval_service.repo.update_status = AsyncMock(return_value=mock_invoice)
        approval_service.repo.commit = AsyncMock()

        await approval_service.approve(1)

        approval_service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        approval_service.ledger_service.record_from_expense.assert_called_once_with(mock_invoice)

    @pytest.mark.asyncio
    async def test_approve_high_value_manager_to_finance(self, approval_service, mock_db):
        """>30K: manager_approved → finance_approved"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.status = "manager_approved"
        mock_invoice.amount = Decimal("50000")

        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        approval_service.repo.update_status = AsyncMock(return_value=mock_invoice)
        approval_service.repo.commit = AsyncMock()

        await approval_service.approve(1)

        approval_service.repo.update_status.assert_called_once_with(mock_invoice, "finance_approved")
        approval_service.ledger_service.record_from_expense.assert_not_called()

    @pytest.mark.asyncio
    async def test_approve_finance_to_verified(self, approval_service, mock_db):
        """finance_approved → verified + 入帳"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.status = "finance_approved"
        mock_invoice.amount = Decimal("50000")
        mock_invoice.case_code = None  # 略過預算檢查

        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        approval_service.repo.update_status = AsyncMock(return_value=mock_invoice)
        approval_service.repo.commit = AsyncMock()

        await approval_service.approve(1)

        approval_service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        approval_service.ledger_service.record_from_expense.assert_called_once_with(mock_invoice)

    @pytest.mark.asyncio
    async def test_approve_already_verified_raises(self, approval_service):
        """已審核的發票不可再次審核"""
        mock_invoice = MagicMock()
        mock_invoice.status = "verified"
        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)

        with pytest.raises(ValueError, match="verified"):
            await approval_service.approve(1)

    @pytest.mark.asyncio
    async def test_approve_threshold_boundary_low(self, approval_service, mock_db):
        """金額剛好 30K (邊界): 二級審核"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.status = "manager_approved"
        mock_invoice.amount = Decimal("30000")
        mock_invoice.case_code = None  # 略過預算檢查

        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        approval_service.repo.update_status = AsyncMock(return_value=mock_invoice)
        approval_service.repo.commit = AsyncMock()

        await approval_service.approve(1)

        approval_service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        approval_service.ledger_service.record_from_expense.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_threshold_boundary_high(self, approval_service, mock_db):
        """金額 30001 (剛過門檻): 三級審核"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.status = "manager_approved"
        mock_invoice.amount = Decimal("30001")

        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        approval_service.repo.update_status = AsyncMock(return_value=mock_invoice)
        approval_service.repo.commit = AsyncMock()

        await approval_service.approve(1)

        approval_service.repo.update_status.assert_called_once_with(mock_invoice, "finance_approved")
        approval_service.ledger_service.record_from_expense.assert_not_called()

    @pytest.mark.asyncio
    async def test_reject_with_reason(self, approval_service):
        """駁回帶原因"""
        mock_invoice = MagicMock()
        mock_invoice.status = "pending"
        mock_invoice.notes = None
        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        approval_service.repo.update_status = AsyncMock(return_value=mock_invoice)

        await approval_service.reject(1, reason="金額有誤")

        approval_service.repo.update_status.assert_called_once_with(
            mock_invoice, "rejected", notes_append="[駁回] 金額有誤"
        )

    @pytest.mark.asyncio
    async def test_reject_manager_approved(self, approval_service):
        """主管已核准的仍可駁回"""
        mock_invoice = MagicMock()
        mock_invoice.status = "manager_approved"
        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        approval_service.repo.update_status = AsyncMock(return_value=mock_invoice)

        await approval_service.reject(1, reason="補充資料")
        approval_service.repo.update_status.assert_called_once_with(
            mock_invoice, "rejected", notes_append="[駁回] 補充資料"
        )

    @pytest.mark.asyncio
    async def test_reject_verified_raises(self, approval_service):
        """已最終通過的不可駁回"""
        mock_invoice = MagicMock()
        mock_invoice.status = "verified"
        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)

        with pytest.raises(ValueError, match="verified"):
            await approval_service.reject(1)

    @pytest.mark.asyncio
    async def test_reject_already_rejected_raises(self, approval_service):
        """已駁回的不可再駁回"""
        mock_invoice = MagicMock()
        mock_invoice.status = "rejected"
        approval_service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)

        with pytest.raises(ValueError, match="rejected"):
            await approval_service.reject(1)


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
        service.repo.delete_entry = AsyncMock(return_value=True)

        result = await service.delete(1)
        assert result is True
        service.repo.delete_entry.assert_called_once_with(mock_ledger)

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


class TestAttachReceipt:
    """attach_receipt 收據影像附加測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.expense_invoice_service import ExpenseInvoiceService
        svc = ExpenseInvoiceService(mock_db)
        svc.repo = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_attach_receipt_success(self, service):
        """成功附加收據影像"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.receipt_image_path = None
        service.repo.get_by_id = AsyncMock(return_value=mock_invoice)
        service.repo.update_fields = AsyncMock(return_value=mock_invoice)

        result = await service.attach_receipt(1, "receipts/abc123.jpg")

        service.repo.update_fields.assert_called_once_with(
            mock_invoice, {"receipt_image_path": "receipts/abc123.jpg"}
        )
        assert result == mock_invoice

    @pytest.mark.asyncio
    async def test_attach_receipt_not_found(self, service):
        """發票不存在時回傳 None"""
        service.repo.get_by_id = AsyncMock(return_value=None)

        result = await service.attach_receipt(999, "receipts/abc.jpg")
        assert result is None

    @pytest.mark.asyncio
    async def test_attach_receipt_overwrite(self, service):
        """覆蓋已有的收據影像路徑"""
        mock_invoice = MagicMock()
        mock_invoice.id = 1
        mock_invoice.receipt_image_path = "receipts/old.jpg"
        service.repo.get_by_id = AsyncMock(return_value=mock_invoice)
        service.repo.update_fields = AsyncMock(return_value=mock_invoice)

        await service.attach_receipt(1, "receipts/new.jpg")

        service.repo.update_fields.assert_called_once_with(
            mock_invoice, {"receipt_image_path": "receipts/new.jpg"}
        )


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


# ============================================================================
# 多幣別支援測試 (Phase 5-4)
# ============================================================================

class TestMultiCurrencySchema:
    """多幣別 Schema 驗證"""

    def test_twd_default_no_extra_fields(self):
        """TWD 預設幣別，無需填入 original_amount/exchange_rate"""
        data = ExpenseInvoiceCreate(
            inv_num="AB12345678",
            date=date(2026, 3, 21),
            amount=Decimal("1050.00"),
        )
        assert data.currency == "TWD"
        assert data.original_amount is None
        assert data.exchange_rate is None
        assert data.amount == Decimal("1050.00")

    def test_usd_auto_calculates_amount(self):
        """USD 幣別自動換算 TWD amount"""
        data = ExpenseInvoiceCreate(
            inv_num="CD99887766",
            date=date(2026, 3, 21),
            amount=Decimal("1"),  # 會被覆蓋
            currency="USD",
            original_amount=Decimal("100.00"),
            exchange_rate=Decimal("32.150000"),
        )
        assert data.currency == "USD"
        assert data.original_amount == Decimal("100.00")
        assert data.exchange_rate == Decimal("32.150000")
        assert data.amount == Decimal("3215.00")

    def test_jpy_auto_calculates_amount(self):
        """JPY 幣別自動換算"""
        data = ExpenseInvoiceCreate(
            inv_num="EF11223344",
            date=date(2026, 3, 21),
            amount=Decimal("1"),
            currency="JPY",
            original_amount=Decimal("10000"),
            exchange_rate=Decimal("0.213400"),
        )
        assert data.amount == Decimal("2134.00")

    def test_cny_auto_calculates_amount(self):
        """CNY 幣別自動換算"""
        data = ExpenseInvoiceCreate(
            inv_num="GH55667788",
            date=date(2026, 3, 21),
            amount=Decimal("1"),
            currency="CNY",
            original_amount=Decimal("500.00"),
            exchange_rate=Decimal("4.450000"),
        )
        assert data.amount == Decimal("2225.00")

    def test_eur_auto_calculates_amount(self):
        """EUR 幣別自動換算"""
        data = ExpenseInvoiceCreate(
            inv_num="IJ99001122",
            date=date(2026, 3, 21),
            amount=Decimal("1"),
            currency="EUR",
            original_amount=Decimal("200.50"),
            exchange_rate=Decimal("34.800000"),
        )
        assert data.amount == Decimal("6977.40")

    def test_non_twd_missing_original_amount_raises(self):
        """非 TWD 缺少 original_amount 應報錯"""
        with pytest.raises(Exception, match="original_amount"):
            ExpenseInvoiceCreate(
                inv_num="AB12345678",
                date=date(2026, 3, 21),
                amount=Decimal("100"),
                currency="USD",
                exchange_rate=Decimal("32.15"),
            )

    def test_non_twd_missing_exchange_rate_raises(self):
        """非 TWD 缺少 exchange_rate 應報錯"""
        with pytest.raises(Exception, match="exchange_rate"):
            ExpenseInvoiceCreate(
                inv_num="AB12345678",
                date=date(2026, 3, 21),
                amount=Decimal("100"),
                currency="USD",
                original_amount=Decimal("100"),
            )

    def test_invalid_currency_raises(self):
        """不支援的幣別應報錯"""
        with pytest.raises(Exception):
            ExpenseInvoiceCreate(
                inv_num="AB12345678",
                date=date(2026, 3, 21),
                amount=Decimal("100"),
                currency="GBP",
            )

    def test_twd_with_optional_currency_fields(self):
        """TWD 也可以帶 original_amount (例 1:1 匯率)"""
        data = ExpenseInvoiceCreate(
            inv_num="KL33445566",
            date=date(2026, 3, 21),
            amount=Decimal("500.00"),
            currency="TWD",
            original_amount=Decimal("500.00"),
            exchange_rate=Decimal("1.000000"),
        )
        assert data.currency == "TWD"
        assert data.amount == Decimal("500.00")


class TestMultiCurrencyService:
    """多幣別 Service 邏輯測試"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.expense_invoice_service import ExpenseInvoiceService
        svc = ExpenseInvoiceService(mock_db)
        svc.repo = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_create_usd_passes_currency_to_model(self, service, mock_db):
        """建立 USD 報銷時 currency/original_amount/exchange_rate 傳入 Model"""
        service.repo.check_duplicate = AsyncMock(return_value=False)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        data = ExpenseInvoiceCreate(
            inv_num="AB12345678",
            date=date(2026, 3, 21),
            amount=Decimal("1"),
            currency="USD",
            original_amount=Decimal("100.00"),
            exchange_rate=Decimal("32.150000"),
        )
        await service.create(data, user_id=1)

        # create() uses db.add() directly
        call_args = mock_db.add.call_args
        invoice_obj = call_args[0][0]
        assert invoice_obj.currency == "USD"
        assert invoice_obj.amount == Decimal("3215.00")

    @pytest.mark.asyncio
    async def test_create_twd_default_currency(self, service, mock_db):
        """建立 TWD 報銷時 currency 預設為 TWD"""
        service.repo.check_duplicate = AsyncMock(return_value=False)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        data = ExpenseInvoiceCreate(
            inv_num="CD99887766",
            date=date(2026, 3, 21),
            amount=Decimal("500.00"),
        )
        await service.create(data, user_id=1)

        call_args = mock_db.add.call_args
        invoice_obj = call_args[0][0]
        assert invoice_obj.currency == "TWD"


# ============================================================================
# 多層審核狀態機測試 (Phase 5-5)
# ============================================================================

class TestApprovalStateMachine:
    """審核狀態機常數與 approval_info 測試"""

    def test_approval_transitions_terminal_states(self):
        """verified/rejected 為終態，無可轉換狀態"""
        from app.schemas.erp.expense import APPROVAL_TRANSITIONS
        assert APPROVAL_TRANSITIONS["verified"] == []
        assert APPROVAL_TRANSITIONS["rejected"] == []

    def test_approval_transitions_pending(self):
        """pending 可轉為 manager_approved 或 rejected"""
        from app.schemas.erp.expense import APPROVAL_TRANSITIONS
        assert "manager_approved" in APPROVAL_TRANSITIONS["pending"]
        assert "rejected" in APPROVAL_TRANSITIONS["pending"]

    def test_approval_transitions_manager_approved(self):
        """manager_approved 可轉為 finance_approved, verified, rejected"""
        from app.schemas.erp.expense import APPROVAL_TRANSITIONS
        allowed = APPROVAL_TRANSITIONS["manager_approved"]
        assert "finance_approved" in allowed
        assert "verified" in allowed
        assert "rejected" in allowed

    def test_approval_threshold_constant(self):
        """審核門檻為 30000"""
        from app.schemas.erp.expense import APPROVAL_THRESHOLD
        assert APPROVAL_THRESHOLD == Decimal("30000")

    def test_get_approval_info_pending(self):
        """pending 的 approval_info"""
        from app.services.expense_invoice_service import ExpenseInvoiceService
        mock_inv = MagicMock()
        mock_inv.status = "pending"
        mock_inv.amount = Decimal("10000")
        info = ExpenseInvoiceService.get_approval_info(mock_inv)
        assert info["approval_level"] == "pending"
        assert info["next_approval"] == "manager"

    def test_get_approval_info_manager_low_value(self):
        """≤30K manager_approved → next=final"""
        from app.services.expense_invoice_service import ExpenseInvoiceService
        mock_inv = MagicMock()
        mock_inv.status = "manager_approved"
        mock_inv.amount = Decimal("25000")
        info = ExpenseInvoiceService.get_approval_info(mock_inv)
        assert info["approval_level"] == "manager"
        assert info["next_approval"] == "final"

    def test_get_approval_info_manager_high_value(self):
        """>30K manager_approved → next=finance"""
        from app.services.expense_invoice_service import ExpenseInvoiceService
        mock_inv = MagicMock()
        mock_inv.status = "manager_approved"
        mock_inv.amount = Decimal("50000")
        info = ExpenseInvoiceService.get_approval_info(mock_inv)
        assert info["approval_level"] == "manager"
        assert info["next_approval"] == "finance"

    def test_get_approval_info_verified(self):
        """verified 終態"""
        from app.services.expense_invoice_service import ExpenseInvoiceService
        mock_inv = MagicMock()
        mock_inv.status = "verified"
        mock_inv.amount = Decimal("10000")
        info = ExpenseInvoiceService.get_approval_info(mock_inv)
        assert info["approval_level"] == "final"
        assert info["next_approval"] is None

    def test_get_approval_info_rejected(self):
        """rejected 終態"""
        from app.services.expense_invoice_service import ExpenseInvoiceService
        mock_inv = MagicMock()
        mock_inv.status = "rejected"
        mock_inv.amount = Decimal("10000")
        info = ExpenseInvoiceService.get_approval_info(mock_inv)
        assert info["approval_level"] is None
        assert info["next_approval"] is None

    def test_determine_next_pending_receipt(self):
        """pending_receipt → pending (via _determine_next_approval on ApprovalService)"""
        from app.services.expense_approval_service import ExpenseApprovalService
        mock_db = AsyncMock()
        svc = ExpenseApprovalService(mock_db)
        # pending_receipt is not in the standard flow, returns current status
        result = svc._determine_next_approval("pending_receipt", Decimal("100"))
        assert result == "pending_receipt"


# ============================================================================
# 預算聯防測試 (Phase B — Budget Audit Control)
# ============================================================================

class TestBudgetAudit:
    """預算聯防：approve() 進入 verified 前檢查專案預算水位"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.expense_approval_service import ExpenseApprovalService
        svc = ExpenseApprovalService(mock_db)
        svc.repo = AsyncMock()
        svc.repo.commit = AsyncMock()
        svc.ledger_service = AsyncMock()
        svc.ledger_service.find_by_source = AsyncMock(return_value=None)
        return svc

    def _make_invoice(self, **overrides):
        defaults = {
            "id": 1,
            "status": "manager_approved",
            "amount": Decimal("10000"),
            "case_code": "P113-001",
        }
        defaults.update(overrides)
        m = MagicMock()
        for k, v in defaults.items():
            setattr(m, k, v)
        return m

    @pytest.mark.asyncio
    async def test_budget_ok_no_warning(self, service, mock_db):
        """預算充足 (<80%)：正常通過，無警告"""
        mock_invoice = self._make_invoice(amount=Decimal("5000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        service.repo.update_status = AsyncMock(return_value=mock_invoice)

        # 模擬: 預算 100,000，累計支出 30,000，本筆 5,000 → 35% 使用率
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Decimal("100000")
        mock_db.execute = AsyncMock(return_value=mock_result)
        service.ledger_service.get_case_balance = AsyncMock(
            return_value={"expense": Decimal("30000"), "income": Decimal("0")}
        )

        result = await service.approve(1)

        service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        service.ledger_service.record_from_expense.assert_called_once()
        assert getattr(result, "_budget_warning", None) is None

    @pytest.mark.asyncio
    async def test_budget_warning_over_80pct(self, service, mock_db):
        """預算 >80%：放行但附帶預警"""
        mock_invoice = self._make_invoice(amount=Decimal("10000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        service.repo.update_status = AsyncMock(return_value=mock_invoice)

        # 模擬: 預算 100,000，累計 75,000，本筆 10,000 → 85% 使用率
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Decimal("100000")
        mock_db.execute = AsyncMock(return_value=mock_result)
        service.ledger_service.get_case_balance = AsyncMock(
            return_value={"expense": Decimal("75000"), "income": Decimal("0")}
        )

        result = await service.approve(1)

        # 仍然核准並入帳
        service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        service.ledger_service.record_from_expense.assert_called_once()
        # 附帶預警
        warning = getattr(result, "_budget_warning", None)
        assert warning is not None
        assert "預算警告" in warning

    @pytest.mark.asyncio
    async def test_budget_block_over_100pct(self, service, mock_db):
        """預算 >100%：攔截審核"""
        mock_invoice = self._make_invoice(amount=Decimal("20000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        service.repo.update_status = AsyncMock(return_value=mock_invoice)

        # 模擬: 預算 100,000，累計 90,000，本筆 20,000 → 110% 使用率
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Decimal("100000")
        mock_db.execute = AsyncMock(return_value=mock_result)
        service.ledger_service.get_case_balance = AsyncMock(
            return_value={"expense": Decimal("90000"), "income": Decimal("0")}
        )

        with pytest.raises(ValueError, match="預算超限"):
            await service.approve(1)

        # 不應入帳
        service.ledger_service.record_from_expense.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_case_code_skips_budget_check(self, service, mock_db):
        """無案號 (一般營運支出)：略過預算檢查"""
        mock_invoice = self._make_invoice(case_code=None)
        service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        service.repo.update_status = AsyncMock(return_value=mock_invoice)

        result = await service.approve(1)

        service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        service.ledger_service.record_from_expense.assert_called_once()
        # 不應呼叫 db.execute (預算查詢)
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_budget_limit_skips_check(self, service, mock_db):
        """案號存在但無預算設定：略過檢查"""
        mock_invoice = self._make_invoice()
        service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        service.repo.update_status = AsyncMock(return_value=mock_invoice)

        # 模擬: 查無 budget_limit
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.approve(1)

        service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        service.ledger_service.record_from_expense.assert_called_once()
        assert getattr(result, "_budget_warning", None) is None

    def test_budget_constants(self):
        """預算門檻常數正確"""
        from app.schemas.erp.expense import BUDGET_WARNING_PCT, BUDGET_BLOCK_PCT
        assert BUDGET_WARNING_PCT == Decimal("80")
        assert BUDGET_BLOCK_PCT == Decimal("100")

    @pytest.mark.asyncio
    async def test_budget_boundary_exactly_80pct(self, service, mock_db):
        """預算剛好 80%：不觸發警告 (>80% 才觸發)"""
        mock_invoice = self._make_invoice(amount=Decimal("10000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        service.repo.update_status = AsyncMock(return_value=mock_invoice)

        # 模擬: 預算 100,000，累計 70,000，本筆 10,000 → 剛好 80%
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Decimal("100000")
        mock_db.execute = AsyncMock(return_value=mock_result)
        service.ledger_service.get_case_balance = AsyncMock(
            return_value={"expense": Decimal("70000"), "income": Decimal("0")}
        )

        result = await service.approve(1)

        service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        assert getattr(result, "_budget_warning", None) is None

    @pytest.mark.asyncio
    async def test_budget_boundary_exactly_100pct(self, service, mock_db):
        """預算剛好 100%：不攔截 (>100% 才攔截)"""
        mock_invoice = self._make_invoice(amount=Decimal("10000"))
        service.repo.get_by_id_for_update = AsyncMock(return_value=mock_invoice)
        service.repo.update_status = AsyncMock(return_value=mock_invoice)

        # 模擬: 預算 100,000，累計 90,000，本筆 10,000 → 剛好 100%
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Decimal("100000")
        mock_db.execute = AsyncMock(return_value=mock_result)
        service.ledger_service.get_case_balance = AsyncMock(
            return_value={"expense": Decimal("90000"), "income": Decimal("0")}
        )

        result = await service.approve(1)

        # 100% 剛好不超限，但會觸發 >80% 的警告
        service.repo.update_status.assert_called_once_with(mock_invoice, "verified")
        warning = getattr(result, "_budget_warning", None)
        assert warning is not None
        assert "預算警告" in warning


# ============================================================================
# Phase 5-6: 收款確認自動入帳測試
# ============================================================================

class TestBillingAutoLedger:
    """ERPBillingService 收款確認 → Ledger 自動入帳"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.erp.billing_service import ERPBillingService
        svc = ERPBillingService(mock_db)
        svc.repo = AsyncMock()
        return svc

    def _make_billing_mock(self, **overrides):
        """建立帶有完整欄位的 billing mock (避免 Pydantic model_validate 失敗)"""
        defaults = {
            "id": 1, "erp_quotation_id": 10,
            "billing_code": None,
            "billing_period": "第1期", "billing_date": date(2026, 3, 1),
            "billing_amount": Decimal("50000"), "invoice_id": None,
            "payment_status": "pending", "payment_date": None,
            "payment_amount": None, "notes": None,
            "invoice_number": None, "created_at": None, "updated_at": None,
        }
        defaults.update(overrides)
        m = MagicMock(spec=list(defaults.keys()))
        for k, v in defaults.items():
            setattr(m, k, v)
        return m

    @pytest.mark.asyncio
    async def test_update_no_status_change_no_ledger(self, service, mock_db):
        """更新備註不觸發入帳 (EventBus not called)"""
        from app.schemas.erp import ERPBillingUpdate
        mock_billing = self._make_billing_mock()
        service.repo.get_by_id = AsyncMock(return_value=mock_billing)

        update_data = ERPBillingUpdate(notes="更新備註")
        with patch("app.core.event_bus.EventBus") as MockBus:
            mock_bus = MagicMock()
            mock_bus.publish = AsyncMock()
            MockBus.get_instance.return_value = mock_bus
            await service.update(1, update_data)
            mock_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_paid_no_double_ledger(self, service, mock_db):
        """已經是 paid 不重複發布事件"""
        from app.schemas.erp import ERPBillingUpdate
        mock_billing = self._make_billing_mock(
            payment_status="paid", payment_amount=Decimal("50000"),
        )
        service.repo.get_by_id = AsyncMock(return_value=mock_billing)

        update_data = ERPBillingUpdate(notes="補充說明")
        with patch("app.core.event_bus.EventBus") as MockBus:
            mock_bus = MagicMock()
            mock_bus.publish = AsyncMock()
            MockBus.get_instance.return_value = mock_bus
            await service.update(1, update_data)
            mock_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_from_billing_creates_income(self):
        """record_from_billing 建立收入記錄"""
        from app.services.finance_ledger_service import FinanceLedgerService
        mock_db = AsyncMock()
        svc = FinanceLedgerService(mock_db)
        svc.repo = AsyncMock()
        svc.repo.create_entry = AsyncMock()

        await svc.record_from_billing(
            billing_id=1,
            case_code="P113-001",
            payment_amount=Decimal("50000"),
            payment_date=date(2026, 3, 21),
            billing_period="第1期",
        )

        call_args = svc.repo.create_entry.call_args[0][0]
        assert call_args.entry_type == "income"
        assert call_args.amount == Decimal("50000")
        assert call_args.case_code == "P113-001"
        assert call_args.source_type == "erp_billing"
        assert call_args.source_id == 1
        assert "第1期" in call_args.description


# ============================================================================
# AP 應付帳款自動拋轉測試 (戰略 A — Vendor Payable → Ledger)
# ============================================================================

class TestVendorPayableAutoLedger:
    """ERPVendorPayableService 付款確認 → Ledger 自動入帳"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.erp.vendor_payable_service import ERPVendorPayableService
        svc = ERPVendorPayableService(mock_db)
        svc.repo = AsyncMock()
        svc.ledger_service = AsyncMock()
        svc.ledger_service.find_by_source = AsyncMock(return_value=None)
        return svc

    def _make_payable_mock(self, **overrides):
        defaults = {
            "id": 1, "erp_quotation_id": 10,
            "vendor_name": "測試廠商", "vendor_code": "V001",
            "payable_amount": Decimal("80000"),
            "description": "外包設計費",
            "due_date": date(2026, 4, 1),
            "paid_date": None, "paid_amount": None,
            "payment_status": "unpaid",
            "invoice_number": None, "notes": None,
            "created_at": None, "updated_at": None,
        }
        defaults.update(overrides)
        m = MagicMock(spec=list(defaults.keys()))
        for k, v in defaults.items():
            setattr(m, k, v)
        return m

    @pytest.mark.asyncio
    async def test_update_to_paid_triggers_ledger(self, service, mock_db):
        """unpaid → paid 觸發 Ledger 入帳"""
        from app.schemas.erp import ERPVendorPayableUpdate

        # 使用普通物件而非 MagicMock，讓 setattr 正常運作
        class FakePayable:
            id = 1
            erp_quotation_id = 10
            vendor_name = "測試廠商"
            vendor_code = "V001"
            vendor_id = 5
            payable_amount = Decimal("80000")
            description = "外包設計費"
            due_date = date(2026, 4, 1)
            paid_date = None
            paid_amount = None
            payment_status = "unpaid"
            invoice_number = None
            notes = None
            created_at = None
            updated_at = None

        payable = FakePayable()
        service.repo.get_by_id = AsyncMock(return_value=payable)

        # 模擬: 查詢案號 (透過 _quotation_repo.get_by_id)
        fake_quotation = MagicMock()
        fake_quotation.case_code = "P113-001"
        service._quotation_repo = MagicMock()
        service._quotation_repo.get_by_id = AsyncMock(return_value=fake_quotation)

        update_data = ERPVendorPayableUpdate(
            payment_status="paid",
            paid_amount=Decimal("80000"),
            paid_date=date(2026, 3, 22),
        )

        await service.update(1, update_data)

        service.ledger_service.record_from_vendor_payable.assert_called_once()
        call_kwargs = service.ledger_service.record_from_vendor_payable.call_args
        assert call_kwargs[1].get("case_code") == "P113-001"

    @pytest.mark.asyncio
    async def test_update_notes_no_ledger(self, service, mock_db):
        """僅更新備註不觸發入帳"""
        from app.schemas.erp import ERPVendorPayableUpdate
        payable = self._make_payable_mock()
        service.repo.get_by_id = AsyncMock(return_value=payable)

        update_data = ERPVendorPayableUpdate(notes="補充資料")
        await service.update(1, update_data)

        service.ledger_service.record_from_vendor_payable.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_paid_no_double_ledger(self, service, mock_db):
        """已經是 paid 狀態不重複入帳"""
        from app.schemas.erp import ERPVendorPayableUpdate
        payable = self._make_payable_mock(
            payment_status="paid", paid_amount=Decimal("80000"),
        )
        service.repo.get_by_id = AsyncMock(return_value=payable)

        update_data = ERPVendorPayableUpdate(notes="補充說明")
        await service.update(1, update_data)

        service.ledger_service.record_from_vendor_payable.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_from_vendor_payable_creates_expense(self):
        """record_from_vendor_payable 建立支出記錄"""
        from app.services.finance_ledger_service import FinanceLedgerService
        mock_db = AsyncMock()
        svc = FinanceLedgerService(mock_db)
        svc.repo = AsyncMock()
        svc.repo.create_entry = AsyncMock()

        await svc.record_from_vendor_payable(
            payable_id=5,
            case_code="P113-002",
            paid_amount=Decimal("120000"),
            paid_date=date(2026, 3, 22),
            vendor_name="大成工程",
            description="基礎施工",
        )

        call_args = svc.repo.create_entry.call_args[0][0]
        assert call_args.entry_type == "expense"
        assert call_args.amount == Decimal("120000")
        assert call_args.case_code == "P113-002"
        assert call_args.source_type == "erp_vendor_payable"
        assert call_args.source_id == 5
        assert "大成工程" in call_args.description
