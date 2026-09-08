# -*- coding: utf-8 -*-
"""
PM 案件服務層單元測試
PMCaseService Unit Tests

使用 Mock 資料庫測試 PMCaseService 的核心方法

執行方式:
    pytest tests/unit/test_services/test_pm_case_service.py -v
"""
import pytest
import sys
import os
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.pm.case_service import PMCaseService
from app.schemas.pm.case import (
    PMCaseCreate, PMCaseUpdate, PMCaseResponse,
    PMCaseListRequest, PMCaseSummary,
)
from app.schemas.common import SortOrder


# ============================================================================
# Helpers
# ============================================================================

def _make_mock_pm_case(
    case_id: int = 1,
    case_code: str = "CK2025_PM_01_001",
    case_name: str = "Test Case",
    year: int = 114,
    category: str = "01",
    status: str = "planning",
    progress: int = 0,
    contract_amount: Decimal = Decimal("500000"),
    client_name: str = "Test Client",
    client_contact: str = "John",
    client_phone: str = "02-1234567",
    start_date: date = None,
    end_date: date = None,
    actual_end_date: date = None,
    location: str = None,
    description: str = None,
    notes: str = None,
    created_by: int = 1,
) -> MagicMock:
    """Build a mock PMCase ORM instance with __table__.columns."""
    mock = MagicMock()
    mock.id = case_id
    mock.case_code = case_code
    mock.case_name = case_name
    mock.year = year
    mock.category = category
    mock.status = status
    mock.progress = progress
    mock.contract_amount = contract_amount
    mock.client_name = client_name
    mock.client_contact = client_contact
    mock.client_phone = client_phone
    mock.start_date = start_date
    mock.end_date = end_date
    mock.actual_end_date = actual_end_date
    mock.location = location
    mock.description = description
    mock.notes = notes
    mock.created_by = created_by
    mock.created_at = datetime(2026, 1, 1)
    mock.updated_at = datetime(2026, 1, 1)

    # Simulate __table__.columns
    col_names = [
        "id", "case_code", "case_name", "year", "category",
        "client_name", "client_contact", "client_phone",
        "contract_amount", "status", "progress",
        "start_date", "end_date", "actual_end_date",
        "location", "description", "notes",
        "created_by", "created_at", "updated_at",
    ]
    columns = []
    for name in col_names:
        col = MagicMock()
        col.name = name
        columns.append(col)
    mock.__table__ = MagicMock()
    mock.__table__.columns = columns
    return mock


# ============================================================================
# Tests
# ============================================================================

class TestPMCaseServiceCreate:
    """create() tests"""

    @pytest.mark.asyncio
    async def test_create_case_with_auto_code(self, mock_db_session):
        """case_code 未提供時自動產生"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository") as MockMR, \
patch("app.services.pm.case_service.CaseCodeService") as MockCode:

            # code service
            code_inst = MockCode.return_value
            code_inst.generate_case_code = AsyncMock(return_value="CK2025_PM_01_001")

            # milestone / staff repos
            MockMR.return_value.get_by_case_id = AsyncMock(return_value=[])
            # PMCaseStaffRepository removed — staff moved to unified table

            # mock db.refresh to populate the object
            created_obj = _make_mock_pm_case(case_code="CK2025_PM_01_001")
            mock_db_session.refresh = AsyncMock(side_effect=lambda _obj: None)
            mock_db_session.flush = AsyncMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.add = MagicMock()
            mock_db_session.execute = AsyncMock(return_value=MagicMock(**{"scalar.return_value": 0, "first.return_value": None}))  # 09-06：同名承攬案查詢用 .first()，MagicMock 為真會誤判「已有同名」  # 09-02 防重查詢

            service = PMCaseService(mock_db_session)
            # Override _to_response to return a predictable result
            service._to_response = AsyncMock(return_value=PMCaseResponse(
                id=1, case_code="CK2025_PM_01_001", case_name="Auto Code Case",
                status="planning",
            ))

            data = PMCaseCreate(case_name="Auto Code Case", year=114, category="01")
            result = await service.create(data, user_id=1)

            assert result.case_code == "CK2025_PM_01_001"
            code_inst.generate_case_code.assert_awaited_once_with("pm", 2025, "01")  # §2.5：民國 114 一律轉西元再給號

    @pytest.mark.asyncio
    async def test_create_case_with_manual_code(self, mock_db_session):
        """case_code 已提供時保留原值"""
        with patch("app.services.pm.case_service.PMCaseRepository"), \
             patch("app.services.pm.case_service.PMMilestoneRepository") as MockMR, \
patch("app.services.pm.case_service.CaseCodeService") as MockCode:

            code_inst = MockCode.return_value
            code_inst.generate_case_code = AsyncMock()
            code_inst.validate_case_code = AsyncMock(return_value=True)  # 09-06：手動案號現在會先驗格式（await）
            code_inst.check_duplicate = AsyncMock(return_value=False)

            MockMR.return_value.get_by_case_id = AsyncMock(return_value=[])
            # PMCaseStaffRepository removed — staff moved to unified table
            mock_db_session.execute = AsyncMock(return_value=MagicMock(**{"scalar.return_value": 0, "first.return_value": None}))
            mock_db_session.refresh = AsyncMock(side_effect=lambda _obj: None)
            mock_db_session.flush = AsyncMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.add = MagicMock()

            service = PMCaseService(mock_db_session)
            service._to_response = AsyncMock(return_value=PMCaseResponse(
                id=1, case_code="MANUAL_CODE_001", case_name="Manual Case",
                status="planning",
            ))

            data = PMCaseCreate(case_name="Manual Case", case_code="MANUAL_CODE_001")
            result = await service.create(data, user_id=1)

            assert result.case_code == "MANUAL_CODE_001"
            code_inst.generate_case_code.assert_not_awaited()


class TestPMCaseServiceGetDetail:
    """get_detail() tests"""

    @pytest.mark.asyncio
    async def test_get_detail_found(self, mock_db_session):
        """Return proper response with milestone/staff counts"""
        mock_case = _make_mock_pm_case()
        milestones = [MagicMock(), MagicMock()]
        staff = [MagicMock()]

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository") as MockMR, \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_case)
            MockMR.return_value.get_by_case_id = AsyncMock(return_value=milestones)
            # PMCaseStaffRepository removed — staff count fixed to 0

            service = PMCaseService(mock_db_session)
            result = await service.get_detail(1)

            assert result is not None
            assert result.id == 1
            assert result.milestone_count == 2
            assert result.staff_count == 0  # staff moved to unified table

    @pytest.mark.asyncio
    async def test_get_detail_not_found(self, mock_db_session):
        """Return None for non-existent case"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            service = PMCaseService(mock_db_session)
            result = await service.get_detail(999)

            assert result is None


class TestPMCaseServiceUpdate:
    """update() tests"""

    @pytest.mark.asyncio
    async def test_update_case(self, mock_db_session):
        """Verify update flow"""
        mock_case = _make_mock_pm_case()

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository") as MockMR, \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_case)
            MockMR.return_value.get_by_case_id = AsyncMock(return_value=[])
            # PMCaseStaffRepository removed — staff moved to unified table

            service = PMCaseService(mock_db_session)
            data = PMCaseUpdate(case_name="Updated Case", status="in_progress")
            result = await service.update(1, data)

            assert result is not None
            mock_db_session.flush.assert_awaited()
            mock_db_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_case_not_found(self, mock_db_session):
        """Return None when case not found"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            service = PMCaseService(mock_db_session)
            result = await service.update(999, PMCaseUpdate(case_name="X"))

            assert result is None


class TestPMCaseServiceDelete:
    """delete() tests"""

    @staticmethod
    def _no_references(mock_db_session):
        """讓引用計數全部回 0 —— 模擬「這個案還沒有任何金流」。"""
        counts = MagicMock()
        counts.quotations = counts.billings = counts.invoices = 0
        counts.payables = counts.ledgers = counts.contracts = 0
        result = MagicMock()
        result.one = MagicMock(return_value=counts)
        mock_db_session.execute = AsyncMock(return_value=result)

    @pytest.mark.asyncio
    async def test_delete_case(self, mock_db_session):
        """未成案且無任何金流 ⇒ 可刪。

        2026-09-08：本測試原本鎖的是「刪除永遠回 True」——那是舊契約。
        `delete()` 現在會擋下已成案／已有金流的案（owner：「避免最後財務無法統整」），
        所以這裡要明確做出「乾淨的案」，否則 MagicMock 的 `project_code`
        是個 truthy 物件，會被判成已成案。
        """
        mock_case = _make_mock_pm_case()
        mock_case.project_code = None
        self._no_references(mock_db_session)
        mock_db_session.delete = AsyncMock()

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_case)

            service = PMCaseService(mock_db_session)
            result = await service.delete(1)

            assert result is True
            mock_db_session.delete.assert_awaited_once_with(mock_case)
            mock_db_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_delete_blocked_when_contracted(self, mock_db_session):
        """已成案 ⇒ 擋下，且**不得呼叫 db.delete**。

        2026-09-08 回歸鎖：此前 `delete()` 是硬刪、零檢查，而 pm_cases 沒有軟刪欄位、
        金流靠 case_code 字串關聯（無外鍵）⇒ 誤刪一筆已成案的 PM，該案的報價單／
        請款／發票／帳本會靜默變成追不回案件的孤兒。沒有這支測試，
        閘門日後被拿掉不會有任何人知道。
        """
        mock_case = _make_mock_pm_case()
        mock_case.project_code = "CK2025_01_01_001"
        self._no_references(mock_db_session)
        mock_db_session.delete = AsyncMock()

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):
            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_case)
            service = PMCaseService(mock_db_session)
            with pytest.raises(ValueError) as exc:
                await service.delete(1)
            # 訊息要說得出擋住的是什麼 —— 只說「不能刪」會讓人想辦法繞過
            assert "已成案" in str(exc.value)
            assert "CK2025_01_01_001" in str(exc.value)
            mock_db_session.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_blocked_when_has_billings(self, mock_db_session):
        """未成案但已有請款 ⇒ 一樣擋下（判準是有沒有留下痕跡，不是狀態欄位怎麼寫）。"""
        mock_case = _make_mock_pm_case()
        mock_case.project_code = None
        counts = MagicMock()
        counts.quotations = 1
        counts.billings = 3
        counts.invoices = counts.payables = counts.ledgers = counts.contracts = 0
        result = MagicMock()
        result.one = MagicMock(return_value=counts)
        mock_db_session.execute = AsyncMock(return_value=result)
        mock_db_session.delete = AsyncMock()

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):
            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_case)
            service = PMCaseService(mock_db_session)
            with pytest.raises(ValueError) as exc:
                await service.delete(1)
            assert "3 筆請款" in str(exc.value)
            mock_db_session.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_case_not_found(self, mock_db_session):
        """Verify deletion returns False for missing case"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            service = PMCaseService(mock_db_session)
            result = await service.delete(999)

            assert result is False


class TestPMCaseServiceList:
    """list_cases() tests"""

    @pytest.mark.asyncio
    async def test_list_cases(self, mock_db_session):
        """Verify batch aggregate delegation"""
        mock_cases = [_make_mock_pm_case(case_id=i, case_code=f"CK2025_PM_01_{str(i).zfill(3)}") for i in range(1, 4)]

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository") as MockMR, \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.filter_cases = AsyncMock(return_value=(mock_cases, 3))
            MockMR.return_value.get_counts_batch = AsyncMock(return_value={})
            # PMCaseStaffRepository removed — staff counts fixed to 0

            service = PMCaseService(mock_db_session)
            params = PMCaseListRequest(page=1, limit=20, year=114, status="planning")
            responses, total = await service.list_cases(params)

            assert total == 3
            assert len(responses) == 3
            MockMR.return_value.get_counts_batch.assert_awaited_once()
            # staff counts assertion removed — unified table

    @pytest.mark.asyncio
    async def test_list_cases_empty(self, mock_db_session):
        """Verify empty result"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.filter_cases = AsyncMock(return_value=([], 0))

            service = PMCaseService(mock_db_session)
            params = PMCaseListRequest(page=1, limit=20)
            responses, total = await service.list_cases(params)

            assert total == 0
            assert len(responses) == 0


class TestPMCaseServiceSummary:
    """get_summary() tests"""

    @pytest.mark.asyncio
    async def test_get_summary(self, mock_db_session):
        """Verify statistics aggregation"""
        summary_data = {
            "total_cases": 10,
            "by_status": {"planning": 3, "in_progress": 5, "completed": 2},
            "by_year": {"114": 7, "113": 3},
            "total_contract_amount": Decimal("5000000"),
        }

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_summary = AsyncMock(return_value=summary_data)

            service = PMCaseService(mock_db_session)
            result = await service.get_summary(year=114)

            assert isinstance(result, PMCaseSummary)
            assert result.total_cases == 10
            assert result.by_status["planning"] == 3
            assert result.total_contract_amount == Decimal("5000000")


class TestPMCaseServiceGenerateCode:
    """generate_case_code() tests"""

    @pytest.mark.asyncio
    async def test_generate_case_code(self, mock_db_session):
        """Verify delegation to CaseCodeService"""
        with patch("app.services.pm.case_service.PMCaseRepository"), \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService") as MockCode:

            code_inst = MockCode.return_value
            code_inst.generate_case_code = AsyncMock(return_value="CK2025_PM_02_005")

            service = PMCaseService(mock_db_session)
            result = await service.generate_case_code(year=114, category="02")

            assert result == "CK2025_PM_02_005"
            code_inst.generate_case_code.assert_awaited_once_with("pm", 114, "02")


# ============================================================================
# P3/P4 Feature Tests
# ============================================================================

class TestPMCaseServiceGantt:
    """generate_gantt() tests — P3-1"""

    @pytest.mark.asyncio
    async def test_gantt_with_milestones(self, mock_db_session):
        """Verify Mermaid Gantt output with mixed statuses"""
        mock_case = _make_mock_pm_case(case_code="CK2025_PM_01_001")

        m1 = MagicMock()
        m1.milestone_name = "設計階段"
        m1.status = "completed"
        m1.planned_date = date(2025, 1, 1)
        m1.actual_date = date(2025, 2, 1)
        m1.sort_order = 1

        m2 = MagicMock()
        m2.milestone_name = "施工階段"
        m2.status = "in_progress"
        m2.planned_date = date(2025, 3, 1)
        m2.actual_date = None
        m2.sort_order = 2

        m3 = MagicMock()
        m3.milestone_name = "驗收"
        m3.status = "overdue"
        m3.planned_date = date(2025, 4, 1)
        m3.actual_date = None
        m3.sort_order = 3

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository") as MockMR, \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_case)
            MockMR.return_value.get_by_case_id = AsyncMock(return_value=[m1, m2, m3])

            service = PMCaseService(mock_db_session)
            result = await service.generate_gantt(1)

            assert result is not None
            assert "gantt" in result
            assert "CK2025_PM_01_001" in result
            assert "done" in result  # completed → done
            assert "active" in result  # in_progress → active
            assert "crit" in result  # overdue → crit
            assert "設計階段" in result
            assert "施工階段" in result
            assert "驗收" in result

    @pytest.mark.asyncio
    async def test_gantt_case_not_found(self, mock_db_session):
        """Return None when case not found"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            service = PMCaseService(mock_db_session)
            result = await service.generate_gantt(999)
            assert result is None

    @pytest.mark.asyncio
    async def test_gantt_no_milestones_with_dates(self, mock_db_session):
        """Gantt with milestones but none have planned_date — still returns header"""
        mock_case = _make_mock_pm_case()
        m1 = MagicMock()
        m1.planned_date = None
        m1.sort_order = 1
        m1.status = "pending"

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository") as MockMR, \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_case)
            MockMR.return_value.get_by_case_id = AsyncMock(return_value=[m1])

            service = PMCaseService(mock_db_session)
            result = await service.generate_gantt(1)
            assert result is not None
            assert "gantt" in result


class TestPMCaseServiceExportCsv:
    """export_csv() tests — P3-3"""

    @pytest.mark.asyncio
    async def test_export_csv_basic(self, mock_db_session):
        """Verify CSV output has BOM and correct columns"""
        mock_cases = [
            _make_mock_pm_case(case_id=1, case_code="CK2025_PM_01_001", case_name="Case A"),
            _make_mock_pm_case(case_id=2, case_code="CK2025_PM_01_002", case_name="Case B"),
        ]

        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.filter_cases = AsyncMock(return_value=(mock_cases, 2))

            service = PMCaseService(mock_db_session)
            csv_str = await service.export_csv(year=114)

            assert csv_str.startswith("\ufeff")  # BOM
            assert "案號" in csv_str
            assert "案名" in csv_str
            assert "CK2025_PM_01_001" in csv_str
            assert "Case A" in csv_str
            assert "Case B" in csv_str

    @pytest.mark.asyncio
    async def test_export_csv_empty(self, mock_db_session):
        """CSV with no data still has header"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.filter_cases = AsyncMock(return_value=([], 0))

            service = PMCaseService(mock_db_session)
            csv_str = await service.export_csv()

            assert csv_str.startswith("\ufeff")
            assert "案號" in csv_str
            lines = csv_str.strip().split("\n")
            assert len(lines) == 1  # Header only


class TestPMCaseServiceYearlyTrend:
    """get_yearly_trend() tests — 使用 SQL 聚合"""

    @pytest.mark.asyncio
    async def test_yearly_trend_multi_year(self, mock_db_session):
        """Verify SQL aggregation delegation"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_yearly_trend_sql = AsyncMock(return_value=[
                {
                    "year": 113, "case_count": 2, "total_contract": Decimal("3000000"),
                    "closed_count": 1, "in_progress_count": 1, "avg_progress": 80,
                },
                {
                    "year": 114, "case_count": 1, "total_contract": Decimal("500000"),
                    "closed_count": 0, "in_progress_count": 0, "avg_progress": 0,
                },
            ])

            service = PMCaseService(mock_db_session)
            result = await service.get_yearly_trend()

            assert len(result) == 2
            assert result[0].year == 113
            assert result[0].case_count == 2
            assert result[0].total_contract == Decimal("3000000")
            assert result[0].closed_count == 1
            assert result[1].year == 114
            MockRepo.return_value.get_yearly_trend_sql.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_yearly_trend_empty(self, mock_db_session):
        """Empty when no cases"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_yearly_trend_sql = AsyncMock(return_value=[])

            service = PMCaseService(mock_db_session)
            result = await service.get_yearly_trend()

            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_yearly_trend_skips_null_year(self, mock_db_session):
        """SQL query already filters year IS NOT NULL"""
        with patch("app.services.pm.case_service.PMCaseRepository") as MockRepo, \
             patch("app.services.pm.case_service.PMMilestoneRepository"), \
patch("app.services.pm.case_service.CaseCodeService"):

            MockRepo.return_value.get_yearly_trend_sql = AsyncMock(return_value=[])

            service = PMCaseService(mock_db_session)
            result = await service.get_yearly_trend()

            assert len(result) == 0
