"""
公文統計服務單元測試

測試範圍：
- get_overall_statistics: 整體統計
- get_filtered_statistics: 篩選統計
- _get_delivery_method_statistics: 發文形式統計
- get_next_send_number: 發文字號生成
- get_document_years: 文檔年度列表

共 6 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from app.services.document_statistics_service import DocumentStatisticsService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    with patch(
        "app.services.document_statistics_service.DocumentStatsRepository"
    ) as MockRepo:
        svc = DocumentStatisticsService(mock_db)
        svc.repository = AsyncMock()
        return svc


# ============================================================================
# get_overall_statistics
# ============================================================================

class TestGetOverallStatistics:
    """整體統計"""

    @pytest.mark.asyncio
    async def test_returns_all_fields(self, service, mock_db):
        """回傳完整統計欄位"""
        service.repository.get_statistics = AsyncMock(return_value={
            "total": 100,
            "by_type": {"發文": 40, "收文": 60},
            "by_month": {"2026-01": 10, "2026-02": 15},
        })

        # Mock current_year_send and delivery stats queries
        scalar_mock = MagicMock()
        scalar_mock.scalar.return_value = 5
        mock_db.execute.return_value = scalar_mock

        result = await service.get_overall_statistics()

        assert result["success"] is True
        assert result["total"] == 100
        assert result["send_count"] == 40
        assert result["receive_count"] == 60
        assert result["current_year_count"] == 25  # sum of by_month
        assert "delivery_method_stats" in result


# ============================================================================
# get_filtered_statistics
# ============================================================================

class TestGetFilteredStatistics:
    """篩選統計"""

    @pytest.mark.asyncio
    async def test_no_filters(self, service, mock_db):
        """無篩選條件"""
        scalar_mock = MagicMock()
        scalar_mock.scalar.return_value = 50
        mock_db.execute.return_value = scalar_mock

        result = await service.get_filtered_statistics()

        assert result["success"] is True
        assert result["filters_applied"] is False

    @pytest.mark.asyncio
    async def test_with_keyword_filter(self, service, mock_db):
        """含關鍵字篩選"""
        scalar_mock = MagicMock()
        scalar_mock.scalar.return_value = 10
        mock_db.execute.return_value = scalar_mock

        result = await service.get_filtered_statistics(keyword="工程")

        assert result["success"] is True
        assert result["filters_applied"] is True


# ============================================================================
# get_next_send_number
# ============================================================================

class TestGetNextSendNumber:
    """發文字號生成"""

    @pytest.mark.asyncio
    async def test_default_prefix(self, service, mock_db):
        """使用預設前綴生成字號"""
        fetchone_mock = MagicMock()
        fetchone_mock.__getitem__ = MagicMock(return_value=3)
        result_mock = MagicMock()
        result_mock.fetchone.return_value = fetchone_mock
        mock_db.execute.return_value = result_mock

        result = await service.get_next_send_number(year=2026)

        assert result["prefix"] == "乾坤測字第"
        assert result["roc_year"] == 115
        assert result["sequence_number"] == 4  # previous max 3 + 1
        assert "乾坤測字第115" in result["full_number"]
        assert result["full_number"].endswith("號")

    @pytest.mark.asyncio
    async def test_first_number_in_year(self, service, mock_db):
        """該年度第一筆（無前序記錄）"""
        fetchone_mock = MagicMock()
        fetchone_mock.__getitem__ = MagicMock(return_value=None)
        result_mock = MagicMock()
        result_mock.fetchone.return_value = fetchone_mock
        mock_db.execute.return_value = result_mock

        result = await service.get_next_send_number(year=2026)

        assert result["sequence_number"] == 1
        assert result["previous_max"] == 0


# ============================================================================
# get_document_years
# ============================================================================

class TestGetDocumentYears:
    """文檔年度列表"""

    @pytest.mark.asyncio
    async def test_returns_sorted_years(self, service, mock_db):
        """回傳降序年度列表"""
        row_2026 = MagicMock()
        row_2026.year = 2026
        row_2025 = MagicMock()
        row_2025.year = 2025
        result_mock = MagicMock()
        result_mock.all.return_value = [row_2026, row_2025]
        mock_db.execute.return_value = result_mock

        years = await service.get_document_years()

        assert years == [2026, 2025]
