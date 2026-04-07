# -*- coding: utf-8 -*-
"""
ERP Billing-to-Ledger 整合測試
ERP Billing Flow Integration Tests

測試覆蓋:
1. 建立請款 (Billing) 關聯到既有報價單 (Quotation)
2. 從請款記錄建立銷項發票 (Invoice)
3. 確認收款 (payment_status → paid)
4. 驗證帳本 (FinanceLedger) 自動建立收入記錄

執行方式:
    cd backend
    python -m pytest tests/integration/test_erp_billing_flow.py -v
    python -m pytest tests/integration/test_erp_billing_flow.py -v -m integration

v1.0.0 - 2026-04-01
"""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.erp import ERPBilling, ERPInvoice, ERPQuotation
from app.extended.models.finance import FinanceLedger
from app.schemas.erp import ERPBillingCreate, ERPBillingUpdate, ERPInvoiceCreate
from app.services.erp.billing_service import ERPBillingService
from app.services.erp.invoice_service import ERPInvoiceService
from app.services.finance_ledger_service import FinanceLedgerService

pytestmark = pytest.mark.integration


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_quotation() -> ERPQuotation:
    """建立 mock 報價單物件，模擬資料庫中已存在的報價"""
    quotation = MagicMock(spec=ERPQuotation)
    quotation.id = 100
    quotation.case_code = "CASE-2026-001"
    quotation.case_name = "測試專案報價"
    quotation.year = 115
    quotation.total_price = Decimal("500000.00")
    quotation.status = "confirmed"
    return quotation


@pytest.fixture
def sample_billing_data() -> dict:
    """範例請款資料"""
    return {
        "erp_quotation_id": 100,
        "billing_period": "第1期",
        "billing_date": date(2026, 4, 1),
        "billing_amount": Decimal("200000.00"),
        "payment_status": "pending",
        "notes": "第一期請款",
    }


@pytest.fixture
def sample_payment_data() -> dict:
    """範例收款確認資料"""
    return {
        "payment_status": "paid",
        "payment_date": date(2026, 4, 15),
        "payment_amount": Decimal("200000.00"),
    }


# ============================================================
# Service 層整合測試 (Mock DB)
# ============================================================


class TestBillingToLedgerFlow:
    """請款 → 發票 → 收款確認 → 帳本自動入帳 完整流程"""

    @pytest.mark.asyncio
    async def test_create_billing(self, mock_db_session, sample_billing_data):
        """Step 1: 建立請款記錄"""
        billing_create = ERPBillingCreate(**sample_billing_data)
        mock_billing = MagicMock(spec=ERPBilling)
        mock_billing.id = 1
        mock_billing.erp_quotation_id = 100
        mock_billing.billing_code = None
        mock_billing.billing_period = "第1期"
        mock_billing.billing_date = date(2026, 4, 1)
        mock_billing.billing_amount = Decimal("200000.00")
        mock_billing.payment_status = "pending"
        mock_billing.payment_date = None
        mock_billing.payment_amount = None
        mock_billing.invoice_id = None
        mock_billing.notes = "第一期請款"
        mock_billing.created_at = None
        mock_billing.updated_at = None

        service = ERPBillingService(mock_db_session)
        service.repo = MagicMock()
        service.repo.create = AsyncMock(return_value=mock_billing)
        service._audit_log = AsyncMock()

        result = await service.create(billing_create)

        assert result.id == 1
        assert result.erp_quotation_id == 100
        assert result.billing_period == "第1期"
        assert result.billing_amount == Decimal("200000.00")
        assert result.payment_status == "pending"
        service.repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invoice_from_billing(self, mock_db_session):
        """Step 2: 從請款記錄建立銷項發票"""
        mock_billing = MagicMock(spec=ERPBilling)
        mock_billing.id = 1
        mock_billing.erp_quotation_id = 100
        mock_billing.billing_amount = Decimal("200000.00")
        mock_billing.billing_period = "第1期"
        mock_billing.invoice_id = None

        mock_invoice = MagicMock(spec=ERPInvoice)
        mock_invoice.id = 10
        mock_invoice.erp_quotation_id = 100
        mock_invoice.invoice_ref = None
        mock_invoice.invoice_number = "INV-2026-0001"
        mock_invoice.invoice_date = date(2026, 4, 5)
        mock_invoice.amount = Decimal("200000.00")
        mock_invoice.tax_amount = Decimal("0")
        mock_invoice.invoice_type = "sales"
        mock_invoice.description = "請款期別: 第1期"
        mock_invoice.status = "issued"
        mock_invoice.billing_id = 1
        mock_invoice.voided_at = None
        mock_invoice.notes = None
        mock_invoice.created_at = None
        mock_invoice.updated_at = None

        # Mock DB query to find the billing
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_billing
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        service = ERPInvoiceService(mock_db_session)
        service.repo = MagicMock()
        service.repo.create = AsyncMock(return_value=mock_invoice)
        service._audit_log = AsyncMock()

        result = await service.create_from_billing(
            billing_id=1,
            invoice_number="INV-2026-0001",
            invoice_date=date(2026, 4, 5),
        )

        assert result.id == 10
        assert result.invoice_number == "INV-2026-0001"
        assert result.amount == Decimal("200000.00")
        assert result.invoice_type == "sales"
        assert result.billing_id == 1
        service.repo.create.assert_called_once()

        # Verify billing was linked to invoice
        assert mock_billing.invoice_id == mock_invoice.id

    @pytest.mark.asyncio
    async def test_create_invoice_from_billing_already_linked(self, mock_db_session):
        """已有發票的請款記錄不能重複開票"""
        mock_billing = MagicMock(spec=ERPBilling)
        mock_billing.id = 1
        mock_billing.invoice_id = 99  # Already linked

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_billing
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = ERPInvoiceService(mock_db_session)

        with pytest.raises(ValueError, match="已有關聯發票"):
            await service.create_from_billing(
                billing_id=1,
                invoice_number="INV-DUP",
            )

    @pytest.mark.asyncio
    async def test_confirm_payment_creates_ledger_entry(
        self, mock_db_session, mock_quotation, sample_payment_data
    ):
        """Step 3+4: 收款確認後發布 billing_paid 事件"""
        # Setup: billing in pending state
        mock_billing = MagicMock(spec=ERPBilling)
        mock_billing.id = 1
        mock_billing.erp_quotation_id = 100
        mock_billing.billing_code = None
        mock_billing.billing_period = "第1期"
        mock_billing.billing_date = date(2026, 4, 1)
        mock_billing.billing_amount = Decimal("200000.00")
        mock_billing.payment_status = "pending"  # Old status
        mock_billing.payment_date = None
        mock_billing.payment_amount = None
        mock_billing.invoice_id = 10
        mock_billing.notes = "第一期請款"
        mock_billing.created_at = None
        mock_billing.updated_at = None

        service = ERPBillingService(mock_db_session)
        service.repo = MagicMock()
        service.repo.get_by_id = AsyncMock(return_value=mock_billing)
        service._quotation_repo = MagicMock()
        service._quotation_repo.get_by_id = AsyncMock(return_value=mock_quotation)
        service._audit_log = AsyncMock()

        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Execute: confirm payment
        update_data = ERPBillingUpdate(**sample_payment_data)

        with patch("app.core.event_bus.EventBus") as MockBus:
            mock_bus_instance = MagicMock()
            mock_bus_instance.publish = AsyncMock()
            MockBus.get_instance.return_value = mock_bus_instance

            result = await service.update(billing_id=1, data=update_data)

        # Verify: billing was updated
        assert result is not None
        assert result.id == 1

        # Verify: billing_paid event was published
        mock_bus_instance.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_ledger_entry_when_status_unchanged(
        self, mock_db_session, mock_quotation
    ):
        """payment_status 未變更為 paid 時，不應發布 billing_paid 事件"""
        mock_billing = MagicMock(spec=ERPBilling)
        mock_billing.id = 1
        mock_billing.erp_quotation_id = 100
        mock_billing.billing_code = None
        mock_billing.billing_period = "第1期"
        mock_billing.billing_date = date(2026, 4, 1)
        mock_billing.billing_amount = Decimal("200000.00")
        mock_billing.payment_status = "pending"
        mock_billing.payment_date = None
        mock_billing.payment_amount = None
        mock_billing.invoice_id = None
        mock_billing.notes = None
        mock_billing.created_at = None
        mock_billing.updated_at = None

        service = ERPBillingService(mock_db_session)
        service.repo = MagicMock()
        service.repo.get_by_id = AsyncMock(return_value=mock_billing)
        service._audit_log = AsyncMock()

        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Update notes only, not payment_status
        update_data = ERPBillingUpdate(notes="更新備註")
        with patch("app.core.event_bus.EventBus") as MockBus:
            mock_bus_instance = MagicMock()
            mock_bus_instance.publish = AsyncMock()
            MockBus.get_instance.return_value = mock_bus_instance

            await service.update(billing_id=1, data=update_data)

            # EventBus should NOT be called (no status change to paid)
            mock_bus_instance.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_ledger_entry_when_already_paid(
        self, mock_db_session, mock_quotation
    ):
        """已是 paid 狀態再次更新，不應重複發布事件"""
        mock_billing = MagicMock(spec=ERPBilling)
        mock_billing.id = 1
        mock_billing.erp_quotation_id = 100
        mock_billing.billing_code = None
        mock_billing.billing_period = "第1期"
        mock_billing.billing_date = date(2026, 4, 1)
        mock_billing.billing_amount = Decimal("200000.00")
        mock_billing.payment_status = "paid"  # Already paid
        mock_billing.payment_date = date(2026, 4, 15)
        mock_billing.payment_amount = Decimal("200000.00")
        mock_billing.invoice_id = 10
        mock_billing.notes = None
        mock_billing.created_at = None
        mock_billing.updated_at = None

        service = ERPBillingService(mock_db_session)
        service.repo = MagicMock()
        service.repo.get_by_id = AsyncMock(return_value=mock_billing)
        service._audit_log = AsyncMock()

        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Re-update with paid status (same as current)
        update_data = ERPBillingUpdate(
            payment_status="paid",
            notes="更新備註，狀態不變",
        )
        with patch("app.core.event_bus.EventBus") as MockBus:
            mock_bus_instance = MagicMock()
            mock_bus_instance.publish = AsyncMock()
            MockBus.get_instance.return_value = mock_bus_instance

            await service.update(billing_id=1, data=update_data)

            # EventBus should NOT be called (old_status == "paid")
            mock_bus_instance.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_ledger_when_payment_amount_missing(
        self, mock_db_session, mock_quotation
    ):
        """收款金額為空時，不應發布事件"""
        mock_billing = MagicMock(spec=ERPBilling)
        mock_billing.id = 1
        mock_billing.erp_quotation_id = 100
        mock_billing.billing_code = None
        mock_billing.billing_period = "第1期"
        mock_billing.billing_date = date(2026, 4, 1)
        mock_billing.billing_amount = Decimal("200000.00")
        mock_billing.payment_status = "pending"
        mock_billing.payment_date = None
        mock_billing.payment_amount = None  # No payment amount
        mock_billing.invoice_id = None
        mock_billing.notes = None
        mock_billing.created_at = None
        mock_billing.updated_at = None

        service = ERPBillingService(mock_db_session)
        service.repo = MagicMock()
        service.repo.get_by_id = AsyncMock(return_value=mock_billing)
        service._quotation_repo = MagicMock()
        service._quotation_repo.get_by_id = AsyncMock(return_value=mock_quotation)
        service._audit_log = AsyncMock()

        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Set status to paid but without payment_amount
        update_data = ERPBillingUpdate(
            payment_status="paid",
            payment_date=date(2026, 4, 15),
            # payment_amount intentionally omitted
        )
        with patch("app.core.event_bus.EventBus") as MockBus:
            mock_bus_instance = MagicMock()
            mock_bus_instance.publish = AsyncMock()
            MockBus.get_instance.return_value = mock_bus_instance

            await service.update(billing_id=1, data=update_data)

            # EventBus should NOT be called (payment_amount is None)
            mock_bus_instance.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_case_code_fallback_when_quotation_has_no_case_code(
        self, mock_db_session
    ):
        """報價單無 case_code 時，事件使用預設 case_code"""
        mock_quotation_no_code = MagicMock(spec=ERPQuotation)
        mock_quotation_no_code.id = 200
        mock_quotation_no_code.case_code = None

        mock_billing = MagicMock(spec=ERPBilling)
        mock_billing.id = 2
        mock_billing.erp_quotation_id = 200
        mock_billing.billing_code = None
        mock_billing.billing_period = "尾款"
        mock_billing.billing_date = date(2026, 4, 1)
        mock_billing.billing_amount = Decimal("100000.00")
        mock_billing.payment_status = "pending"
        mock_billing.payment_date = None
        mock_billing.payment_amount = None
        mock_billing.invoice_id = None
        mock_billing.notes = None
        mock_billing.created_at = None
        mock_billing.updated_at = None

        service = ERPBillingService(mock_db_session)
        service.repo = MagicMock()
        service.repo.get_by_id = AsyncMock(return_value=mock_billing)
        service._quotation_repo = MagicMock()
        service._quotation_repo.get_by_id = AsyncMock(
            return_value=mock_quotation_no_code
        )
        service._audit_log = AsyncMock()

        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        mock_db_session.commit = AsyncMock()

        update_data = ERPBillingUpdate(
            payment_status="paid",
            payment_date=date(2026, 4, 20),
            payment_amount=Decimal("100000.00"),
        )
        with patch("app.core.event_bus.EventBus") as MockBus:
            mock_bus_instance = MagicMock()
            mock_bus_instance.publish = AsyncMock()
            MockBus.get_instance.return_value = mock_bus_instance

            await service.update(billing_id=2, data=update_data)

            # Should publish event with fallback case_code
            mock_bus_instance.publish.assert_called_once()
            event = mock_bus_instance.publish.call_args[0][0]
            assert event.payload["case_code"] == "一般營運"

    @pytest.mark.asyncio
    async def test_delete_billing(self, mock_db_session):
        """刪除請款記錄"""
        service = ERPBillingService(mock_db_session)
        service.repo = MagicMock()
        service.repo.delete = AsyncMock(return_value=True)
        service._audit_log = AsyncMock()

        result = await service.delete(billing_id=1)

        assert result is True
        service.repo.delete.assert_called_once_with(1)


class TestLedgerRecordFromBilling:
    """FinanceLedgerService.record_from_billing 單元驗證"""

    @pytest.mark.asyncio
    async def test_record_from_billing_creates_income_entry(self, mock_db_session):
        """確認產生的帳本記錄欄位正確"""
        mock_db_session.add = MagicMock()
        mock_db_session.flush = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        service = FinanceLedgerService(mock_db_session)

        # Mock repo.create_entry to capture the ledger object
        created_ledger = None

        async def capture_create(ledger):
            nonlocal created_ledger
            created_ledger = ledger
            ledger.id = 99
            return ledger

        service.repo = MagicMock()
        service.repo.create_entry = AsyncMock(side_effect=capture_create)

        result = await service.record_from_billing(
            billing_id=1,
            case_code="CASE-2026-001",
            payment_amount=Decimal("200000.00"),
            payment_date=date(2026, 4, 15),
            billing_period="第1期",
        )

        # Verify ledger record fields
        assert created_ledger is not None
        assert created_ledger.amount == Decimal("200000.00")
        assert created_ledger.entry_type == "income"
        assert created_ledger.category == "收款"
        assert created_ledger.source_type == "erp_billing"
        assert created_ledger.source_id == 1
        assert created_ledger.case_code == "CASE-2026-001"
        assert created_ledger.transaction_date == date(2026, 4, 15)
        assert "第1期" in created_ledger.description

    @pytest.mark.asyncio
    async def test_record_from_billing_without_period(self, mock_db_session):
        """無期別時摘要仍正確"""
        service = FinanceLedgerService(mock_db_session)

        created_ledger = None

        async def capture_create(ledger):
            nonlocal created_ledger
            created_ledger = ledger
            ledger.id = 100
            return ledger

        service.repo = MagicMock()
        service.repo.create_entry = AsyncMock(side_effect=capture_create)

        await service.record_from_billing(
            billing_id=5,
            case_code="CASE-2026-002",
            payment_amount=150000,
            billing_period=None,
        )

        assert created_ledger is not None
        assert created_ledger.source_id == 5
        assert "第" not in (created_ledger.description or "")
        assert "請款收款" in created_ledger.description

    @pytest.mark.asyncio
    async def test_record_from_billing_converts_non_decimal(self, mock_db_session):
        """非 Decimal 金額應自動轉換"""
        service = FinanceLedgerService(mock_db_session)

        created_ledger = None

        async def capture_create(ledger):
            nonlocal created_ledger
            created_ledger = ledger
            ledger.id = 101
            return ledger

        service.repo = MagicMock()
        service.repo.create_entry = AsyncMock(side_effect=capture_create)

        # Pass int instead of Decimal
        await service.record_from_billing(
            billing_id=3,
            case_code="CASE-INT",
            payment_amount=300000,
        )

        assert created_ledger is not None
        assert isinstance(created_ledger.amount, Decimal)
        assert created_ledger.amount == Decimal("300000")
