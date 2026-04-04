"""
Phase 7-D Dashboard 擴展 — 月度趨勢 + 預算排行 單元測試

Version: 1.0.0
Created: 2026-03-22
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMonthlyTrendRepository:
    """FinancialSummaryRepository.get_monthly_trend 測試"""

    @pytest.mark.asyncio
    async def test_monthly_trend_returns_12_months(self):
        """預設回傳 12 個月份"""
        mock_db = AsyncMock()

        # 模擬 DB 回傳 3 個月有資料
        mock_rows = [
            MagicMock(month="2026-01", income=Decimal("100000"), expense=Decimal("40000")),
            MagicMock(month="2026-02", income=Decimal("80000"), expense=Decimal("50000")),
            MagicMock(month="2026-03", income=Decimal("120000"), expense=Decimal("60000")),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        trend = await repo.get_monthly_trend(months=12)

        assert len(trend) == 12
        # 有資料的月份應有正確數值
        jan = next(t for t in trend if t["month"] == "2026-01")
        assert jan["income"] == Decimal("100000")
        assert jan["expense"] == Decimal("40000")
        assert jan["net"] == Decimal("60000")

    @pytest.mark.asyncio
    async def test_monthly_trend_empty_months_filled(self):
        """沒有資料的月份應補零"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        trend = await repo.get_monthly_trend(months=3)

        assert len(trend) == 3
        for item in trend:
            assert item["income"] == Decimal("0")
            assert item["expense"] == Decimal("0")
            assert item["net"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_monthly_trend_with_case_code(self):
        """指定案號應傳入 WHERE 條件"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        trend = await repo.get_monthly_trend(months=6, case_code="PRJ-001")

        assert len(trend) == 6
        # 驗證 execute 被呼叫 (SQL 中包含 case_code 條件)
        mock_db.execute.assert_called_once()


class TestBudgetRankingRepository:
    """FinancialSummaryRepository.get_budget_ranking 測試"""

    @pytest.mark.asyncio
    async def test_budget_ranking_calculates_usage_pct(self):
        """正確計算使用率百分比"""
        mock_db = AsyncMock()

        mock_rows = [
            MagicMock(case_code="PRJ-001", total_income=Decimal("1000000"), total_expense=Decimal("850000")),
            MagicMock(case_code="PRJ-002", total_income=Decimal("500000"), total_expense=Decimal("600000")),
            MagicMock(case_code="PRJ-003", total_income=Decimal("200000"), total_expense=Decimal("50000")),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        items, total = await repo.get_budget_ranking(top_n=10)

        assert total == 3
        assert len(items) <= 10

        # PRJ-002 usage = 120% → critical, 排最前 (desc)
        assert items[0]["case_code"] == "PRJ-002"
        assert items[0]["usage_pct"] == 120.0
        assert items[0]["alert"] == "critical"

        # PRJ-001 usage = 85% → warning
        assert items[1]["case_code"] == "PRJ-001"
        assert items[1]["usage_pct"] == 85.0
        assert items[1]["alert"] == "warning"

        # PRJ-003 usage = 25% → normal
        assert items[2]["case_code"] == "PRJ-003"
        assert items[2]["usage_pct"] == 25.0
        assert items[2]["alert"] == "normal"

    @pytest.mark.asyncio
    async def test_budget_ranking_zero_income_excluded(self):
        """收入為零的專案 usage_pct 為 None"""
        mock_db = AsyncMock()

        mock_rows = [
            MagicMock(case_code="PRJ-X", total_income=Decimal("0"), total_expense=Decimal("1000")),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        items, total = await repo.get_budget_ranking()

        assert total == 1
        assert items[0]["usage_pct"] is None

    @pytest.mark.asyncio
    async def test_budget_ranking_top_n_limit(self):
        """Top N 限制"""
        mock_db = AsyncMock()

        mock_rows = [
            MagicMock(case_code=f"PRJ-{i:03d}", total_income=Decimal("100000"), total_expense=Decimal(str(i * 1000)))
            for i in range(1, 21)
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        items, total = await repo.get_budget_ranking(top_n=5)

        assert total == 20
        assert len(items) == 5


class TestBatchProjectSummaries:
    """FinancialSummaryRepository.get_batch_project_summaries 測試"""

    @pytest.mark.asyncio
    async def test_batch_returns_correct_count(self):
        """批量查詢回傳與輸入等量結果"""
        mock_db = AsyncMock()

        # 模擬 3 個專案主檔
        proj1 = MagicMock(project_code="A001", project_name="專案A", contract_amount=Decimal("1000000"))
        proj2 = MagicMock(project_code="A002", project_name="專案B", contract_amount=Decimal("500000"))
        proj3 = MagicMock(project_code="A003", project_name="專案C", contract_amount=None)

        # 模擬 3 次 execute: project, expense, ledger
        mock_proj_result = MagicMock()
        mock_proj_result.scalars.return_value.all.return_value = [proj1, proj2, proj3]

        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = [
            MagicMock(case_code="A001", cnt=5, total=Decimal("300000")),
            MagicMock(case_code="A002", cnt=2, total=Decimal("100000")),
        ]

        mock_ledger_result = MagicMock()
        mock_ledger_result.all.return_value = [
            MagicMock(case_code="A001", entry_type="income", total=Decimal("800000")),
            MagicMock(case_code="A001", entry_type="expense", total=Decimal("300000")),
            MagicMock(case_code="A002", entry_type="expense", total=Decimal("100000")),
        ]

        mock_quot_result = MagicMock()
        mock_quot_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[mock_proj_result, mock_expense_result, mock_ledger_result, mock_quot_result])

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        results = await repo.get_batch_project_summaries(["A001", "A002", "A003"])

        assert len(results) == 3
        assert results[0].case_code == "A001"
        assert results[0].expense_invoice_count == 5
        assert results[0].total_income == Decimal("800000")
        assert results[0].budget_alert == "normal"  # 300k/1M = 30%

        assert results[1].case_code == "A002"
        assert results[1].budget_alert == "normal"  # 100k/500k = 20%

        assert results[2].case_code == "A003"
        assert results[2].budget_used_percentage is None  # no budget

    @pytest.mark.asyncio
    async def test_batch_empty_list(self):
        """空案號列表回傳空"""
        mock_db = AsyncMock()
        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)
        results = await repo.get_batch_project_summaries([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_missing_project(self):
        """找不到專案主檔的案號回傳 None"""
        mock_db = AsyncMock()

        mock_proj_result = MagicMock()
        mock_proj_result.scalars.return_value.all.return_value = []  # 沒有專案

        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = []

        mock_ledger_result = MagicMock()
        mock_ledger_result.all.return_value = []

        mock_quot_result = MagicMock()
        mock_quot_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[mock_proj_result, mock_expense_result, mock_ledger_result, mock_quot_result])

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        results = await repo.get_batch_project_summaries(["MISSING"])
        assert len(results) == 1
        assert results[0] is None

    @pytest.mark.asyncio
    async def test_batch_budget_alert_levels(self):
        """驗證 critical (>95%) / warning (>80%) / normal 判定"""
        mock_db = AsyncMock()

        proj_crit = MagicMock(project_code="C1", project_name="超支", contract_amount=Decimal("100000"))
        proj_warn = MagicMock(project_code="C2", project_name="警告", contract_amount=Decimal("100000"))

        mock_proj_result = MagicMock()
        mock_proj_result.scalars.return_value.all.return_value = [proj_crit, proj_warn]
        mock_expense_result = MagicMock()
        mock_expense_result.all.return_value = []
        mock_ledger_result = MagicMock()
        mock_ledger_result.all.return_value = [
            MagicMock(case_code="C1", entry_type="expense", total=Decimal("96000")),  # 96%
            MagicMock(case_code="C2", entry_type="expense", total=Decimal("85000")),  # 85%
        ]
        mock_quot_result = MagicMock()
        mock_quot_result.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[mock_proj_result, mock_expense_result, mock_ledger_result, mock_quot_result])

        from app.repositories.erp.financial_summary_repository import FinancialSummaryRepository
        repo = FinancialSummaryRepository(mock_db)

        results = await repo.get_batch_project_summaries(["C1", "C2"])
        assert results[0].budget_alert == "critical"
        assert results[1].budget_alert == "warning"


class TestFinancialSummaryServiceDashboard:
    """FinancialSummaryService dashboard 方法測試"""

    @pytest.mark.asyncio
    async def test_get_monthly_trend_service(self):
        """Service 層正確委派 Repository"""
        mock_db = AsyncMock()

        with patch(
            "app.services.financial_summary_service.FinancialSummaryRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_monthly_trend = AsyncMock(return_value=[
                {"month": "2026-03", "income": Decimal("100"), "expense": Decimal("50"), "net": Decimal("50")},
            ])

            from app.services.financial_summary_service import FinancialSummaryService
            service = FinancialSummaryService(mock_db)

            result = await service.get_monthly_trend(months=1, case_code="PRJ-001")

            assert result["case_code"] == "PRJ-001"
            assert len(result["months"]) == 1
            mock_repo.get_monthly_trend.assert_awaited_once_with(months=1, case_code="PRJ-001")


class TestSchemaValidation:
    """Schema 驗證測試"""

    def test_monthly_trend_request_defaults(self):
        from app.schemas.erp.financial_summary import MonthlyTrendRequest
        req = MonthlyTrendRequest()
        assert req.months == 12
        assert req.case_code is None

    def test_monthly_trend_request_bounds(self):
        from app.schemas.erp.financial_summary import MonthlyTrendRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MonthlyTrendRequest(months=0)
        with pytest.raises(ValidationError):
            MonthlyTrendRequest(months=37)

    def test_budget_ranking_request_defaults(self):
        from app.schemas.erp.financial_summary import BudgetRankingRequest
        req = BudgetRankingRequest()
        assert req.top_n == 15
        assert req.order == "desc"

    def test_budget_ranking_request_invalid_order(self):
        from app.schemas.erp.financial_summary import BudgetRankingRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BudgetRankingRequest(order="invalid")

    def test_monthly_trend_item(self):
        from app.schemas.erp.financial_summary import MonthlyTrendItem
        item = MonthlyTrendItem(month="2026-03", income=Decimal("100"), expense=Decimal("50"), net=Decimal("50"))
        assert item.month == "2026-03"
        assert item.net == Decimal("50")

    def test_budget_ranking_item_alert(self):
        from app.schemas.erp.financial_summary import BudgetRankingItem
        item = BudgetRankingItem(
            case_code="PRJ-001",
            total_expense=Decimal("90000"),
            total_income=Decimal("100000"),
            usage_pct=90.0,
            alert="warning",
        )
        assert item.alert == "warning"
