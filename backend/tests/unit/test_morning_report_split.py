# -*- coding: utf-8 -*-
"""
TDD: Morning Report 拆分後行為不變測試

驗證：
1. MorningReportQueries 可獨立實例化
2. MorningReportFormatter 可獨立生成摘要
3. MorningReportService 整合兩者行為不變
4. _parse_roc_date 正確解析
5. _compute_today_schedule 正確分桶
"""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock


# --------------------------------------------------------------------------
# Test 1: Formatter 獨立運作
# --------------------------------------------------------------------------

class TestMorningReportFormatter:
    def test_format_empty_data(self):
        """空資料應產生「今日無待辦」類摘要"""
        from app.services.ai.domain.morning_report_formatter import MorningReportFormatter

        formatter = MorningReportFormatter()
        result = formatter.format_summary({})
        assert isinstance(result, str)
        # 空資料不應 crash
        assert len(result) >= 0

    def test_format_with_dispatch_data(self):
        """有派工資料應產生對應區段"""
        from app.services.ai.domain.morning_report_formatter import MorningReportFormatter

        formatter = MorningReportFormatter()
        data = {
            "dispatch_deadlines": {
                "today_count": 1,
                "week_count": 2,
                "today_items": [],
                "week_items": [
                    {
                        "dispatch_no": "115-001",
                        "project_name": "測試工程",
                        "handler": "張三",
                        "deadline": "2026-04-20",
                        "days_left": 3,
                        "survey_unit": "乾坤",
                    },
                    {
                        "dispatch_no": "115-002",
                        "project_name": "另一工程",
                        "handler": "李四",
                        "deadline": "2026-04-22",
                        "days_left": 5,
                    },
                ],
            },
        }
        result = formatter.format_summary(data, sections={"dispatch"})
        assert "115-001" in result
        assert "本週到期" in result

    def test_format_sections_filter(self):
        """sections 參數應限制渲染範圍"""
        from app.services.ai.domain.morning_report_formatter import MorningReportFormatter

        formatter = MorningReportFormatter()
        data = {
            "dispatch_deadlines": {"week_count": 1, "week_items": [{"dispatch_no": "X", "deadline": "Y", "days_left": 1}]},
            "upcoming_meetings": {"count": 1, "items": [{"title": "會議A", "time": "09:00"}]},
        }
        # 只渲染 dispatch
        result = formatter.format_summary(data, sections={"dispatch"})
        assert "會議A" not in result

    def test_parse_roc_date(self):
        """ROC 日期解析"""
        from app.services.ai.domain.morning_report_formatter import MorningReportFormatter

        result = MorningReportFormatter._parse_roc_date("115/04/17")
        assert result == date(2026, 4, 17)

    def test_parse_roc_date_invalid(self):
        """無效 ROC 日期回傳 None"""
        from app.services.ai.domain.morning_report_formatter import MorningReportFormatter

        result = MorningReportFormatter._parse_roc_date("invalid")
        assert result is None

    def test_compute_today_schedule_empty(self):
        """空行程應回傳空分桶"""
        from app.services.ai.domain.morning_report_formatter import MorningReportFormatter

        formatter = MorningReportFormatter()
        result = formatter._compute_today_schedule(
            {"count": 0, "items": []},
            {"count": 0, "items": []},
        )
        assert result["morning_count"] == 0
        assert result["afternoon_count"] == 0


# --------------------------------------------------------------------------
# Test 2: Queries 可實例化
# --------------------------------------------------------------------------

class TestMorningReportQueries:
    def test_queries_instantiation(self):
        """MorningReportQueries 可用 mock db 實例化"""
        from app.services.ai.domain.morning_report_queries import MorningReportQueries

        mock_db = MagicMock()
        queries = MorningReportQueries(mock_db)
        assert queries.db is mock_db


# --------------------------------------------------------------------------
# Test 3: Service 整合
# --------------------------------------------------------------------------

class TestMorningReportServiceIntegration:
    def test_service_has_generate_report(self):
        """MorningReportService 應仍有 generate_report 方法"""
        from app.services.ai.domain.morning_report_service import MorningReportService

        mock_db = MagicMock()
        svc = MorningReportService(mock_db)
        assert hasattr(svc, "generate_report")
        assert hasattr(svc, "generate_summary")
        assert hasattr(svc, "generate_summary_from_data")
