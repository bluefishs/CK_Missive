# -*- coding: utf-8 -*-
"""MorningReportService 會議 / 現勘 預警單元測試

驗證純函數：現勘關鍵字偵測、時間格式化、摘要輸出分類。
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.domain.morning_report_service import MorningReportService


@pytest.fixture
def service():
    db = MagicMock()
    return MorningReportService(db)


class TestSiteVisitDetection:
    """_is_site_visit 以 title 關鍵字判定為現勘。"""

    @pytest.mark.parametrize("title", [
        "會勘通知 — 桃園大溪區",
        "現勘排程：台 61 線邊坡",
        "地政事務所複丈勘查",
        "工地勘驗（檢送成果）",
        "第二次履勘會議",
        "現場勘查",
        "辦理現場會勘",
    ])
    def test_site_visit_keywords_detected(self, service, title):
        assert service._is_site_visit(title) is True

    @pytest.mark.parametrize("title", [
        "週會",
        "月度檢討會議",
        "專案啟動會議",
        "預算審查",
        "",
        None,
    ])
    def test_non_site_visit_titles(self, service, title):
        assert service._is_site_visit(title) is False


class TestFormatEventTime:
    """_format_event_time 依 all_day 輸出正確格式。"""

    def test_timed_event(self, service):
        dt = datetime(2026, 4, 16, 14, 30)
        assert service._format_event_time(dt, all_day=False) == "04/16 14:30"

    def test_all_day_event(self, service):
        dt = datetime(2026, 4, 16, 0, 0)
        assert service._format_event_time(dt, all_day=True) == "04/16 全天"

    def test_none_start(self, service):
        assert service._format_event_time(None, all_day=False) == ""


class TestSummaryIncludesMeetingSections:
    """generate_summary_from_data 對新 section 產出正確文案。"""

    @pytest.mark.asyncio
    async def test_meetings_and_site_visits_in_summary(self, service):
        data = {
            "upcoming_meetings": {
                "count": 2,
                "items": [
                    {
                        "title": "Q2 檢討會議",
                        "start_date": "2026-04-16",
                        "time_str": "04/16 10:00",
                        "location": "本社會議室",
                        "days_left": 1,
                    },
                    {
                        "title": "月度進度會議",
                        "start_date": "2026-04-18",
                        "time_str": "04/18 14:00",
                        "location": "",
                        "days_left": 3,
                    },
                ],
            },
            "upcoming_site_visits": {
                "count": 1,
                "items": [
                    {
                        "title": "TY-20260416 大溪邊坡現勘",
                        "start_date": "2026-04-16",
                        "time_str": "04/16 現勘",
                        "location": "大溪區中正路",
                        "days_left": 1,
                        "source": "dispatch",
                    },
                ],
            },
        }
        # 其他 section 讓 generate_summary_from_data 走 fallback 不發 Gemma
        service.db = MagicMock()

        # proactive trigger 會呼叫 DB，以 mock 阻隔
        async def _no_advice(*a, **kw):
            raise RuntimeError("skip ai")

        import app.core.ai_connector as ai_conn_mod
        orig = getattr(ai_conn_mod, "get_ai_connector", None)
        ai_conn_mod.get_ai_connector = lambda: MagicMock(
            chat_completion=AsyncMock(side_effect=_no_advice)
        )

        try:
            summary = await service.generate_summary_from_data(data)
        finally:
            if orig:
                ai_conn_mod.get_ai_connector = orig

        assert "近期會議 2 場" in summary
        assert "近期現勘 1 場" in summary
        assert "Q2 檢討會議" in summary
        assert "大溪邊坡現勘" in summary
        # 緊急度 emoji 出現
        assert "📅 明日" in summary or "📅 1 天後" in summary
        assert "🏗️" in summary
