# -*- coding: utf-8 -*-
"""
ERP 報價服務層單元測試
ERPQuotationService Unit Tests

使用 Mock 資料庫測試 ERPQuotationService 的核心方法 (含損益計算)

執行方式:
    pytest tests/unit/test_services/test_erp_quotation_service.py -v
"""
import pytest
import sys
import os
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.erp.quotation_service import ERPQuotationService
from app.schemas.erp.quotation import (
    ERPQuotationCreate, ERPQuotationUpdate, ERPQuotationResponse,
    ERPQuotationListRequest, ERPProfitSummary,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_mock_quotation(
    qid: int = 1,
    case_code: str = "CK2025_FN_01_001",
    case_name: str = "Test Quotation",
    year: int = 114,
    total_price: Decimal = Decimal("1050000"),
    tax_amount: Decimal = Decimal("50000"),
    outsourcing_fee: Decimal = Decimal("300000"),
    personnel_fee: Decimal = Decimal("200000"),
    overhead_fee: Decimal = Decimal("100000"),
    other_cost: Decimal = Decimal("50000"),
    status: str = "draft",
    notes: str = None,
    created_by: int = 1,
) -> MagicMock:
    """Build a mock ERPQuotation ORM instance with __table__.columns."""
    mock = MagicMock()
    mock.id = qid
    mock.case_code = case_code
    mock.case_name = case_name
    mock.year = year
    mock.total_price = total_price
    mock.tax_amount = tax_amount
    mock.outsourcing_fee = outsourcing_fee
    mock.personnel_fee = personnel_fee
    mock.overhead_fee = overhead_fee
    mock.other_cost = other_cost
    mock.status = status
    mock.notes = notes
    mock.budget_limit = None
    mock.created_by = created_by
    mock.created_at = datetime(2026, 1, 1)
    mock.updated_at = datetime(2026, 1, 1)

    col_names = [
        "id", "case_code", "case_name", "year",
        "total_price", "tax_amount",
        "outsourcing_fee", "personnel_fee", "overhead_fee", "other_cost",
        "budget_limit",
        "status", "notes", "created_by", "created_at", "updated_at",
    ]
    columns = []
    for name in col_names:
        col = MagicMock()
        col.name = name
        columns.append(col)
    mock.__table__ = MagicMock()
    mock.__table__.columns = columns
    return mock


# 2026-08-18：公司固定利潤率（公司留成）由 `_to_response` 讀設定表取得。
#
# 這些測試驗的是**毛利算法**，不是設定查詢 —— 但它們用 `mock_db_session`
# （`execute` 是一支通用 AsyncMock），而我在 `_to_response` 前面加了一次
# `db.execute` 之後，**後續每個 mock 回傳都往後錯一位**：
# `_actual_cost` 拿到的不再是它預期的那個值，`Decimal(str(...))` 直接爆。
#
# 修法是把比率查詢明確 patch 掉，而不是在測試裡排出正確的 mock 序列 ——
# 後者會讓這些測試對「服務內部查詢的順序」敏感，而那不是它們該關心的事。
# 比率本身的行為另有專屬驗證（純函式四情境＋端到端設值還原）。
_RATE = "app.services.erp.quotation_service.get_company_profit_rate"


def _patch_all_repos():
    """Context manager that patches all 5 dependencies of ERPQuotationService."""
    return (
        patch("app.services.erp.quotation_service.ERPQuotationRepository"),
        patch("app.services.erp.quotation_service.ERPInvoiceRepository"),
        patch("app.services.erp.quotation_service.ERPBillingRepository"),
        patch("app.services.erp.quotation_service.ERPVendorPayableRepository"),
        patch("app.services.erp.quotation_service.CaseCodeService"),
    )


# ============================================================================
# compute_profit() — Pure Static
# ============================================================================

class TestComputeProfit:
    """compute_profit static method tests"""

    def test_normal_profit(self):
        """Standard profit calculation"""
        q = _make_mock_quotation(
            total_price=Decimal("1050000"),
            tax_amount=Decimal("50000"),
            outsourcing_fee=Decimal("300000"),
            personnel_fee=Decimal("200000"),
            overhead_fee=Decimal("100000"),
            other_cost=Decimal("50000"),
        )
        result = ERPQuotationService.compute_profit(q)

        # revenue = 1_050_000 - 50_000 = 1_000_000
        # total_cost = 300k + 200k + 100k + 50k = 650_000
        # gross_profit = 1_000_000 - 650_000 = 350_000
        # gross_margin = 350_000 / 1_000_000 * 100 = 35.00
        assert result["total_cost"] == Decimal("650000")
        assert result["gross_profit"] == Decimal("350000")
        assert result["gross_margin"] == Decimal("35.00")
        assert result["net_profit"] == Decimal("350000")

    def test_zero_revenue_no_margin(self):
        """gross_margin is None when revenue = 0"""
        q = _make_mock_quotation(total_price=Decimal("0"), tax_amount=Decimal("0"))
        result = ERPQuotationService.compute_profit(q)
        assert result["gross_margin"] is None

    def test_negative_profit(self):
        """Negative gross_profit when costs exceed revenue"""
        q = _make_mock_quotation(
            total_price=Decimal("100000"),
            tax_amount=Decimal("0"),
            outsourcing_fee=Decimal("200000"),
            personnel_fee=Decimal("0"),
            overhead_fee=Decimal("0"),
            other_cost=Decimal("0"),
        )
        result = ERPQuotationService.compute_profit(q)
        assert result["gross_profit"] == Decimal("-100000")

    def test_none_values_treated_as_zero(self):
        """None amounts default to 0"""
        q = _make_mock_quotation()
        q.total_price = None
        q.tax_amount = None
        q.outsourcing_fee = None
        q.personnel_fee = None
        q.overhead_fee = None
        q.other_cost = None

        result = ERPQuotationService.compute_profit(q)
        assert result["total_cost"] == Decimal("0")
        assert result["gross_profit"] == Decimal("0")
        assert result["gross_margin"] is None


# ============================================================================
# CRUD Tests
# ============================================================================

class TestERPQuotationServiceCreate:
    """create() tests"""

    @pytest.mark.asyncio
    async def test_create_quotation_with_auto_code(self, mock_db_session):
        """case_code not provided triggers auto-generation"""
        mock_q = _make_mock_quotation(case_code="CK2025_FN_01_001")

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService") as MockCode:

            code_inst = MockCode.return_value
            code_inst.generate_case_code = AsyncMock(return_value="CK2025_FN_01_001")
            MockRepo.return_value.create = AsyncMock(return_value=mock_q)

            service = ERPQuotationService(mock_db_session)
            service._to_response = AsyncMock(return_value=ERPQuotationResponse(
                id=1, case_code="CK2025_FN_01_001", status="draft",
            ))

            data = ERPQuotationCreate(case_name="Auto ERP", year=114)
            result = await service.create(data, user_id=1)

            assert result.case_code == "CK2025_FN_01_001"
            code_inst.generate_case_code.assert_awaited_once_with("erp", 114, "01")

    @pytest.mark.asyncio
    async def test_create_quotation_with_manual_code(self, mock_db_session):
        """Provided case_code is preserved"""
        mock_q = _make_mock_quotation(case_code="MANUAL_FN_001")

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService") as MockCode:

            code_inst = MockCode.return_value
            code_inst.generate_case_code = AsyncMock()
            MockRepo.return_value.create = AsyncMock(return_value=mock_q)

            service = ERPQuotationService(mock_db_session)
            service._validate_case_code = AsyncMock()  # 避免 PM import 產生未 await coroutine
            service._to_response = AsyncMock(return_value=ERPQuotationResponse(
                id=1, case_code="MANUAL_FN_001", status="draft",
            ))

            data = ERPQuotationCreate(case_name="Manual ERP", case_code="MANUAL_FN_001")
            result = await service.create(data, user_id=1)

            assert result.case_code == "MANUAL_FN_001"
            code_inst.generate_case_code.assert_not_awaited()


class TestERPQuotationServiceGetDetail:
    """get_detail() tests"""

    @pytest.mark.asyncio
    async def test_get_detail_with_financials(self, mock_db_session):
        """Verify financial calculations are included in response"""
        mock_q = _make_mock_quotation()

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository") as MockInv, \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBill, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository") as MockPay, \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_q)
            MockInv.return_value.get_by_quotation_id = AsyncMock(return_value=[MagicMock(), MagicMock()])
            MockBill.return_value.get_by_quotation_id = AsyncMock(return_value=[MagicMock()])
            MockBill.return_value.get_total_billed = AsyncMock(return_value=Decimal("500000"))
            MockBill.return_value.get_total_received = AsyncMock(return_value=Decimal("300000"))
            MockPay.return_value.get_total_payable = AsyncMock(return_value=Decimal("200000"))
            MockPay.return_value.get_total_paid = AsyncMock(return_value=Decimal("100000"))

            # 2026-08-16 起 `_to_response` 會查統一帳本算「實際成本」。
            # `mock_db_session.execute` 是通用 AsyncMock，`.scalar()` 回 MagicMock，
            # 而 `Decimal(str(MagicMock))` 直接爆 —— 這兩支測試因此自 08-16 起就是紅的
            # （基線錄於 08-15，所以它們被算成「新增失敗」，但**不是今天造成的**）。
            #
            # 明確給 0：這兩支驗的是估列毛利與聚合欄位，
            # 實際成本另有自己的驗證，不該讓它的查詢決定這裡的成敗。
            # ⚠️ 直接設 `execute.return_value.scalar.return_value` 沒有用：
            # `execute` 是 AsyncMock，它的子屬性也是 AsyncMock ——
            # `scalar()` 同步呼叫回的是 coroutine 而不是設定的值
            #（症狀就是那句 `coroutine ... was never awaited`）。
            # 必須明確給一個 MagicMock 當結果物件。
            _res = MagicMock()
            _res.scalar.return_value = 0
            mock_db_session.execute.return_value = _res

            service = ERPQuotationService(mock_db_session)
            result = await service.get_detail(1)

            assert result is not None
            assert result.id == 1
            assert result.total_cost == Decimal("650000")
            assert result.gross_profit == Decimal("350000")
            assert result.gross_margin == Decimal("35.00")
            assert result.invoice_count == 2
            assert result.billing_count == 1
            assert result.total_billed == Decimal("500000")
            assert result.total_received == Decimal("300000")
            assert result.total_payable == Decimal("200000")
            assert result.total_paid == Decimal("100000")

    @pytest.mark.asyncio
    async def test_get_detail_not_found(self, mock_db_session):
        """Return None for non-existent quotation"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            service = ERPQuotationService(mock_db_session)
            result = await service.get_detail(999)

            assert result is None


class TestERPQuotationServiceUpdate:
    """update() tests"""

    @pytest.mark.asyncio
    async def test_update_quotation(self, mock_db_session):
        """Verify update flow via repo.update()"""
        mock_q = _make_mock_quotation()

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository") as MockInv, \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBill, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository") as MockPay, \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.update = AsyncMock(return_value=mock_q)
            MockInv.return_value.get_by_quotation_id = AsyncMock(return_value=[])
            MockBill.return_value.get_by_quotation_id = AsyncMock(return_value=[])
            MockBill.return_value.get_total_billed = AsyncMock(return_value=Decimal("0"))
            MockBill.return_value.get_total_received = AsyncMock(return_value=Decimal("0"))
            MockPay.return_value.get_total_payable = AsyncMock(return_value=Decimal("0"))
            MockPay.return_value.get_total_paid = AsyncMock(return_value=Decimal("0"))

            # `_to_response` 自 08-16 起會查統一帳本算實際成本（見上方說明）
            _res = MagicMock()
            _res.scalar.return_value = 0
            mock_db_session.execute.return_value = _res

            service = ERPQuotationService(mock_db_session)
            data = ERPQuotationUpdate(status="confirmed", total_price=Decimal("2000000"))
            result = await service.update(1, data)

            assert result is not None
            MockRepo.return_value.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_quotation_not_found(self, mock_db_session):
        """Return None when quotation not found"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.update = AsyncMock(return_value=None)

            # 同上：`_to_response` 的實際成本查詢需要一個可轉 Decimal 的值
            # ⚠️ 直接設 `execute.return_value.scalar.return_value` 沒有用：
            # `execute` 是 AsyncMock，它的子屬性也是 AsyncMock ——
            # `scalar()` 同步呼叫回的是 coroutine 而不是設定的值
            #（症狀就是那句 `coroutine ... was never awaited`）。
            # 必須明確給一個 MagicMock 當結果物件。
            _res = MagicMock()
            _res.scalar.return_value = 0
            mock_db_session.execute.return_value = _res

            service = ERPQuotationService(mock_db_session)
            result = await service.update(999, ERPQuotationUpdate(status="confirmed"))

            assert result is None


class TestERPQuotationServiceDelete:
    """delete() tests"""

    @pytest.mark.asyncio
    async def test_delete_quotation(self, mock_db_session):
        """Verify soft deletion sets deleted_at when no paid records"""
        from unittest.mock import MagicMock
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBilling, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository") as MockPayable, \
             patch("app.services.erp.quotation_service.CaseCodeService"), \
             patch("app.services.erp.quotation_service.FinanceLedgerService"):

            mock_quotation = MagicMock()
            mock_quotation.deleted_at = None
            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_quotation)
            MockBilling.return_value.get_by_quotation_id = AsyncMock(return_value=[])
            MockPayable.return_value.get_by_quotation_id = AsyncMock(return_value=[])

            service = ERPQuotationService(mock_db_session)
            result = await service.delete(1)

            assert result is True
            assert mock_quotation.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_blocked_by_paid_billing(self, mock_db_session):
        """Verify deletion blocked when paid billings exist"""
        from unittest.mock import MagicMock
        with patch("app.services.erp.quotation_service.ERPQuotationRepository"), \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBilling, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            paid = MagicMock()
            paid.payment_status = "paid"
            MockBilling.return_value.get_by_quotation_id = AsyncMock(return_value=[paid])

            service = ERPQuotationService(mock_db_session)
            with pytest.raises(ValueError, match="已收款帳單"):
                await service.delete(1)

    @pytest.mark.asyncio
    async def test_delete_blocked_by_paid_payable(self, mock_db_session):
        """Verify deletion blocked when paid vendor payables exist"""
        from unittest.mock import MagicMock
        with patch("app.services.erp.quotation_service.ERPQuotationRepository"), \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBilling, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository") as MockPayable, \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockBilling.return_value.get_by_quotation_id = AsyncMock(return_value=[])
            paid = MagicMock()
            paid.payment_status = "paid"
            MockPayable.return_value.get_by_quotation_id = AsyncMock(return_value=[paid])

            service = ERPQuotationService(mock_db_session)
            with pytest.raises(ValueError, match="已付款的廠商應付"):
                await service.delete(1)

    @pytest.mark.asyncio
    async def test_delete_quotation_not_found(self, mock_db_session):
        """Verify soft deletion returns False for missing quotation"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBilling, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository") as MockPayable, \
             patch("app.services.erp.quotation_service.CaseCodeService"), \
             patch("app.services.erp.quotation_service.FinanceLedgerService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)
            MockBilling.return_value.get_by_quotation_id = AsyncMock(return_value=[])
            MockPayable.return_value.get_by_quotation_id = AsyncMock(return_value=[])

            service = ERPQuotationService(mock_db_session)
            result = await service.delete(999)

            assert result is False


class TestERPQuotationServiceList:
    """list_quotations() tests — 使用批次聚合"""

    @pytest.mark.asyncio
    async def test_list_quotations(self, mock_db_session):
        """Verify batch aggregate delegation"""
        mock_items = [_make_mock_quotation(qid=i) for i in range(1, 4)]

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository") as MockInv, \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBill, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository") as MockPay, \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.filter_quotations = AsyncMock(return_value=(mock_items, 3))
            MockBill.return_value.get_aggregates_batch = AsyncMock(return_value={})
            MockPay.return_value.get_aggregates_batch = AsyncMock(return_value={})
            MockInv.return_value.get_counts_by_quotation_ids = AsyncMock(return_value={})

            service = ERPQuotationService(mock_db_session)
            params = ERPQuotationListRequest(page=1, limit=20, year=114)
            responses, total = await service.list_quotations(params)

            assert total == 3
            assert len(responses) == 3
            MockBill.return_value.get_aggregates_batch.assert_awaited_once()
            MockPay.return_value.get_aggregates_batch.assert_awaited_once()


class TestERPQuotationServiceProfitSummary:
    """get_profit_summary() tests"""

    @pytest.mark.asyncio
    async def test_get_profit_summary(self, mock_db_session):
        """Verify profit summary aggregation — 使用批次聚合"""
        q1 = _make_mock_quotation(
            qid=1, total_price=Decimal("1050000"), tax_amount=Decimal("50000"),
            outsourcing_fee=Decimal("300000"), personnel_fee=Decimal("200000"),
            overhead_fee=Decimal("100000"), other_cost=Decimal("50000"),
        )
        q2 = _make_mock_quotation(
            qid=2, total_price=Decimal("525000"), tax_amount=Decimal("25000"),
            outsourcing_fee=Decimal("100000"), personnel_fee=Decimal("100000"),
            overhead_fee=Decimal("50000"), other_cost=Decimal("25000"),
        )

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBill, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.filter_quotations = AsyncMock(return_value=([q1, q2], 2))
            MockBill.return_value.get_aggregates_batch = AsyncMock(return_value={
                1: {"total_billed": Decimal("200000"), "total_received": Decimal("100000")},
                2: {"total_billed": Decimal("200000"), "total_received": Decimal("100000")},
            })

            service = ERPQuotationService(mock_db_session)
            result = await service.get_profit_summary(year=114)

            assert isinstance(result, ERPProfitSummary)
            assert result.case_count == 2
            assert result.total_revenue == Decimal("1500000")
            assert result.total_cost == Decimal("925000")
            assert result.total_gross_profit == Decimal("575000")
            assert result.avg_gross_margin == Decimal("38.33")
            assert result.total_billed == Decimal("400000")
            assert result.total_received == Decimal("200000")
            assert result.total_outstanding == Decimal("200000")

    @pytest.mark.asyncio
    async def test_get_profit_summary_empty(self, mock_db_session):
        """Empty summary when no quotations"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.filter_quotations = AsyncMock(return_value=([], 0))

            service = ERPQuotationService(mock_db_session)
            result = await service.get_profit_summary()

            assert result.case_count == 0
            assert result.total_revenue == Decimal("0")
            assert result.avg_gross_margin is None


# ============================================================================
# P3/P4 Feature Tests
# ============================================================================

class TestERPQuotationServiceProfitTrend:
    """get_profit_trend() tests — 使用 SQL 聚合"""

    @pytest.mark.asyncio
    async def test_profit_trend_multi_year(self, mock_db_session):
        """Verify multi-year SQL aggregation delegation"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.get_yearly_trend_sql = AsyncMock(return_value=[
                {
                    "year": 113, "revenue": Decimal("1000000"), "cost": Decimal("650000"),
                    "gross_profit": Decimal("350000"), "gross_margin": Decimal("35.00"),
                    "case_count": 1,
                },
                {
                    "year": 114, "revenue": Decimal("500000"), "cost": Decimal("275000"),
                    "gross_profit": Decimal("225000"), "gross_margin": Decimal("45.00"),
                    "case_count": 1,
                },
            ])

            service = ERPQuotationService(mock_db_session)
            result = await service.get_profit_trend()

            assert len(result) == 2
            assert result[0].year == 113
            assert result[0].gross_margin == Decimal("35.00")
            assert result[1].year == 114
            assert result[1].gross_margin == Decimal("45.00")
            MockRepo.return_value.get_yearly_trend_sql.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_profit_trend_empty(self, mock_db_session):
        """Empty trend when no quotations"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockRepo.return_value.get_yearly_trend_sql = AsyncMock(return_value=[])

            service = ERPQuotationService(mock_db_session)
            result = await service.get_profit_trend()

            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_profit_trend_skips_null_year(self, mock_db_session):
        """SQL query already filters year IS NOT NULL"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            # SQL already excludes NULL years, so repo returns empty
            MockRepo.return_value.get_yearly_trend_sql = AsyncMock(return_value=[])

            service = ERPQuotationService(mock_db_session)
            result = await service.get_profit_trend()

            assert len(result) == 0


class TestERPQuotationServiceExportCsv:
    """export_csv() tests — P3-3"""

    @pytest.mark.asyncio
    async def test_export_csv_basic(self, mock_db_session):
        """CSV output contains BOM, header, and data rows"""
        items = [
            _make_mock_quotation(qid=1, case_code="CK2025_FN_01_001", case_name="Q1"),
            _make_mock_quotation(qid=2, case_code="CK2025_FN_01_002", case_name="Q2"),
        ]

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service_io.ERPQuotationRepository") as MockIORepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockIORepo.return_value.filter_quotations = AsyncMock(return_value=(items, 2))

            service = ERPQuotationService(mock_db_session)
            csv_str = await service.export_csv(year=114)

            assert csv_str.startswith("\ufeff")
            assert "案號" in csv_str
            assert "毛利" in csv_str
            assert "CK2025_FN_01_001" in csv_str
            assert "Q2" in csv_str

    @pytest.mark.asyncio
    async def test_export_csv_empty(self, mock_db_session):
        """Empty CSV has header only"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service_io.ERPQuotationRepository") as MockIORepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"),              patch(_RATE, AsyncMock(return_value=Decimal("0"))):

            MockIORepo.return_value.filter_quotations = AsyncMock(return_value=([], 0))

            service = ERPQuotationService(mock_db_session)
            csv_str = await service.export_csv()

            assert csv_str.startswith("\ufeff")
            lines = csv_str.strip().split("\n")
            assert len(lines) == 1


class TestERPBudgetControl:
    """Budget control tests — P4-2"""

    def test_budget_usage_calculation(self):
        """Verify budget_limit and usage calculation in response schema"""
        resp = ERPQuotationResponse(
            id=1, case_code="TEST", status="draft",
            total_cost=Decimal("800000"),
            budget_limit=Decimal("1000000"),
        )
        assert resp.budget_limit == Decimal("1000000")
        # budget_usage_pct is computed: (total_cost/budget_limit)*100
        if resp.budget_limit and resp.total_cost:
            usage = float(resp.total_cost) / float(resp.budget_limit) * 100
            assert usage == 80.0

    def test_is_over_budget(self):
        """Detect over-budget condition"""
        resp = ERPQuotationResponse(
            id=1, case_code="TEST", status="draft",
            total_cost=Decimal("1200000"),
            budget_limit=Decimal("1000000"),
        )
        is_over = (resp.total_cost or 0) > (resp.budget_limit or 0)
        assert is_over is True

    def test_not_over_budget(self):
        """Under-budget condition"""
        resp = ERPQuotationResponse(
            id=1, case_code="TEST", status="draft",
            total_cost=Decimal("500000"),
            budget_limit=Decimal("1000000"),
        )
        is_over = (resp.total_cost or 0) > (resp.budget_limit or 0)
        assert is_over is False

    def test_no_budget_limit(self):
        """No budget_limit set — no over-budget"""
        resp = ERPQuotationResponse(
            id=1, case_code="TEST", status="draft",
            total_cost=Decimal("500000"),
            budget_limit=None,
        )
        assert resp.budget_limit is None
        assert resp.is_over_budget is False
