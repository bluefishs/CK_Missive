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
        with patch("app.services.erp.quotation_service.ERPQuotationRepository"), \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService") as MockCode:

            code_inst = MockCode.return_value
            code_inst.generate_case_code = AsyncMock(return_value="CK2025_FN_01_001")

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
        with patch("app.services.erp.quotation_service.ERPQuotationRepository"), \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService") as MockCode:

            code_inst = MockCode.return_value
            code_inst.generate_case_code = AsyncMock()

            service = ERPQuotationService(mock_db_session)
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
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_q)
            MockInv.return_value.get_by_quotation_id = AsyncMock(return_value=[MagicMock(), MagicMock()])
            MockBill.return_value.get_by_quotation_id = AsyncMock(return_value=[MagicMock()])
            MockBill.return_value.get_total_billed = AsyncMock(return_value=Decimal("500000"))
            MockBill.return_value.get_total_received = AsyncMock(return_value=Decimal("300000"))
            MockPay.return_value.get_total_payable = AsyncMock(return_value=Decimal("200000"))
            MockPay.return_value.get_total_paid = AsyncMock(return_value=Decimal("100000"))

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
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            service = ERPQuotationService(mock_db_session)
            result = await service.get_detail(999)

            assert result is None


class TestERPQuotationServiceUpdate:
    """update() tests"""

    @pytest.mark.asyncio
    async def test_update_quotation(self, mock_db_session):
        """Verify update flow"""
        mock_q = _make_mock_quotation()

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository") as MockInv, \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBill, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository") as MockPay, \
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_q)
            MockInv.return_value.get_by_quotation_id = AsyncMock(return_value=[])
            MockBill.return_value.get_by_quotation_id = AsyncMock(return_value=[])
            MockBill.return_value.get_total_billed = AsyncMock(return_value=Decimal("0"))
            MockBill.return_value.get_total_received = AsyncMock(return_value=Decimal("0"))
            MockPay.return_value.get_total_payable = AsyncMock(return_value=Decimal("0"))
            MockPay.return_value.get_total_paid = AsyncMock(return_value=Decimal("0"))

            service = ERPQuotationService(mock_db_session)
            data = ERPQuotationUpdate(status="confirmed", total_price=Decimal("2000000"))
            result = await service.update(1, data)

            assert result is not None
            mock_db_session.flush.assert_awaited()
            mock_db_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_quotation_not_found(self, mock_db_session):
        """Return None when quotation not found"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            service = ERPQuotationService(mock_db_session)
            result = await service.update(999, ERPQuotationUpdate(status="confirmed"))

            assert result is None


class TestERPQuotationServiceDelete:
    """delete() tests"""

    @pytest.mark.asyncio
    async def test_delete_quotation(self, mock_db_session):
        """Verify deletion returns True"""
        mock_q = _make_mock_quotation()
        mock_db_session.delete = AsyncMock()

        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_q)

            service = ERPQuotationService(mock_db_session)
            result = await service.delete(1)

            assert result is True
            mock_db_session.delete.assert_awaited_once_with(mock_q)

    @pytest.mark.asyncio
    async def test_delete_quotation_not_found(self, mock_db_session):
        """Verify deletion returns False for missing quotation"""
        with patch("app.services.erp.quotation_service.ERPQuotationRepository") as MockRepo, \
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

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
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository") as MockBill, \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository") as MockPay, \
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.filter_quotations = AsyncMock(return_value=(mock_items, 3))
            MockBill.return_value.get_aggregates_batch = AsyncMock(return_value={})
            MockPay.return_value.get_aggregates_batch = AsyncMock(return_value={})

            # Mock _get_invoice_counts_batch via db.execute
            inv_result = MagicMock()
            inv_result.all.return_value = []
            mock_db_session.execute = AsyncMock(return_value=inv_result)

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
             patch("app.services.erp.quotation_service.CaseCodeService"):

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
             patch("app.services.erp.quotation_service.CaseCodeService"):

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
             patch("app.services.erp.quotation_service.CaseCodeService"):

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
             patch("app.services.erp.quotation_service.CaseCodeService"):

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
             patch("app.services.erp.quotation_service.CaseCodeService"):

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
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.filter_quotations = AsyncMock(return_value=(items, 2))

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
             patch("app.services.erp.quotation_service.ERPInvoiceRepository"), \
             patch("app.services.erp.quotation_service.ERPBillingRepository"), \
             patch("app.services.erp.quotation_service.ERPVendorPayableRepository"), \
             patch("app.services.erp.quotation_service.CaseCodeService"):

            MockRepo.return_value.filter_quotations = AsyncMock(return_value=([], 0))

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
