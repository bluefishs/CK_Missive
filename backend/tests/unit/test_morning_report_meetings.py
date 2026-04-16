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


class TestComputeTodaySchedule:
    """_compute_today_schedule 分桶 + 衝突偵測"""

    def test_empty_schedule(self, service):
        result = service._compute_today_schedule(
            {"items": []}, {"items": []}
        )
        assert result["total"] == 0
        assert result["conflicts"] == []
        assert result["overload"] is False

    def test_buckets_morning_afternoon_evening(self, service):
        meetings = {
            "items": [
                {"title": "早會", "days_left": 0, "time_str": "04/16 09:00"},
                {"title": "午會", "days_left": 0, "time_str": "04/16 14:00"},
                {"title": "晚會", "days_left": 0, "time_str": "04/16 19:30"},
            ]
        }
        result = service._compute_today_schedule(meetings, {"items": []})
        assert result["total"] == 3
        assert result["morning"] == 1
        assert result["afternoon"] == 1
        assert result["evening"] == 1

    def test_conflict_detected_within_30min(self, service):
        meetings = {
            "items": [
                {"title": "A 會議", "days_left": 0, "time_str": "04/16 10:00"},
                {"title": "B 會議", "days_left": 0, "time_str": "04/16 10:20"},  # 20 min gap
            ]
        }
        result = service._compute_today_schedule(meetings, {"items": []})
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["gap_minutes"] == 20

    def test_no_conflict_when_30min_plus(self, service):
        meetings = {
            "items": [
                {"title": "A", "days_left": 0, "time_str": "04/16 10:00"},
                {"title": "B", "days_left": 0, "time_str": "04/16 10:30"},  # exactly 30
            ]
        }
        result = service._compute_today_schedule(meetings, {"items": []})
        assert result["conflicts"] == []

    def test_overload_flag_at_5_plus(self, service):
        items = [
            {"title": f"會 {i}", "days_left": 0, "time_str": f"04/16 {9 + i}:00"}
            for i in range(5)
        ]
        result = service._compute_today_schedule({"items": items}, {"items": []})
        assert result["total"] == 5
        assert result["overload"] is True

    def test_site_visit_with_no_time_excluded_from_buckets(self, service):
        site_visits = {
            "items": [
                {"title": "派工現勘", "days_left": 0, "time_str": "04/16 現勘", "source": "dispatch"},
            ]
        }
        result = service._compute_today_schedule({"items": []}, site_visits)
        assert result["total"] == 1
        assert result["morning"] + result["afternoon"] + result["evening"] == 0

    def test_cross_day_events_excluded(self, service):
        meetings = {
            "items": [
                {"title": "明日", "days_left": 1, "time_str": "04/17 10:00"},
                {"title": "後日", "days_left": 2, "time_str": "04/18 14:00"},
            ]
        }
        result = service._compute_today_schedule(meetings, {"items": []})
        assert result["total"] == 0


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


class TestMorningReportRegression:
    """Regression tests for commits 098fc38/4467f75/22fd75d/4bb3f95 — 固化晨報 4 主題聚焦與純文字輸出。

    這些 commit 反覆調整過濾/輸出邏輯，以此測試固化避免再度漂移。
    """

    @pytest.mark.asyncio
    async def test_dispatch_progress_tag_rendered(self, service):
        """commit 098fc38: dispatch items 帶 work_record progress 標籤，輸出應含『〔進度〕』。"""
        data = {
            "dispatch_deadlines": {
                "week_count": 1,
                "today_count": 0,
                "today_items": [],
                "week_items": [
                    {
                        "dispatch_no": "TY-20260416-001",
                        "project_name": "大溪邊坡專案",
                        "sub_case": "",
                        "handler": "張工程師",
                        "deadline": "2026-04-20",
                        "days_left": 4,
                        "progress": "現勘完成",
                    }
                ],
            }
        }
        summary = await service.generate_summary_from_data(data)
        assert "〔現勘完成〕" in summary
        assert "本週到期派工 1 筆" in summary

    @pytest.mark.asyncio
    async def test_overdue_dispatch_progress_tag(self, service):
        """逾期派工同樣需要 progress 標籤輔助承辦人辨識狀態。"""
        data = {
            "overdue_items": {
                "dispatch_count": 1,
                "dispatch_items": [
                    {
                        "dispatch_no": "TY-20260401-003",
                        "project_name": "XX 工程",
                        "handler": "李技師",
                        "overdue_days": 5,
                        "progress": "初勘",
                    }
                ],
            }
        }
        summary = await service.generate_summary_from_data(data)
        assert "🚨 逾期 5 天" in summary
        assert "〔初勘〕" in summary

    @pytest.mark.asyncio
    async def test_plain_text_no_title_truncation(self, service):
        """commit 4467f75: 純文字模式 + 標題不截斷 — 長標題完整保留。"""
        long_title = "第三次 Q2 跨部門協調會議（含法務/財務/工程三方聯席審查）"
        data = {
            "upcoming_meetings": {
                "count": 1,
                "items": [
                    {
                        "title": long_title,
                        "start_date": "2026-04-17",
                        "time_str": "04/17 10:00",
                        "location": "會議室 A",
                        "days_left": 1,
                    }
                ],
            }
        }
        summary = await service.generate_summary_from_data(data)
        assert long_title in summary, "長標題不得截斷"
        assert "..." not in summary.split(long_title)[0][-5:], "標題前不得有截斷符號"

    @pytest.mark.asyncio
    async def test_empty_report_fallback_message(self, service):
        """commit 4bb3f95: 無任何 section 資料時，輸出固定 fallback 訊息。"""
        summary = await service.generate_summary_from_data({})
        assert "晨報" in summary
        assert "無待處理" in summary

    @pytest.mark.asyncio
    async def test_only_four_themes_in_summary_header(self, service):
        """commit 4bb3f95: 摘要 header 只聚焦 4 主題（派工/會議/現勘/遺漏建檔），
        其他 legacy section（新收公文、待審費用、里程碑...）不應洩漏到 parts 裡。"""
        data = {
            "dispatch_deadlines": {"week_count": 1, "week_items": [
                {"dispatch_no": "X", "project_name": "P", "handler": "H",
                 "deadline": "2026-04-20", "days_left": 4, "progress": ""}
            ]},
            "upcoming_meetings": {"count": 1, "items": [
                {"title": "T", "start_date": "2026-04-17", "time_str": "04/17 10:00",
                 "location": "", "days_left": 1}
            ]},
            "upcoming_site_visits": {"count": 0, "items": []},
            "missing_calendar_events": {"count": 0, "items": []},
        }
        summary = await service.generate_summary_from_data(data)
        forbidden_legacy_keywords = ["新收公文", "待審費用", "近期里程碑", "標案訂閱"]
        for kw in forbidden_legacy_keywords:
            assert kw not in summary, f"legacy section '{kw}' 不應出現在 4 主題聚焦的晨報"

    @pytest.mark.asyncio
    async def test_pm_milestone_section_when_opted_in(self, service):
        """B2: pm_milestone section 在 sections={'all'} 時出現。"""
        data = {
            "pm_overdue_milestones": {
                "count": 1,
                "items": [
                    {
                        "milestone_name": "送審成果報告",
                        "planned_date": "2026-04-01",
                        "status": "overdue",
                        "case_code": "CK-2026-003",
                        "case_name": "邊坡整治",
                        "overdue_days": 15,
                    }
                ],
            }
        }
        summary = await service.generate_summary_from_data(data, sections={"all"})
        assert "PM 逾期里程碑 1 項" in summary
        assert "CK-2026-003" in summary
        assert "送審成果報告" in summary

    @pytest.mark.asyncio
    async def test_pm_milestone_hidden_by_default(self, service):
        """B2: pm_milestone 預設不出現。"""
        data = {"pm_overdue_milestones": {"count": 2, "items": [
            {"milestone_name": "X", "overdue_days": 5, "case_code": "Y",
             "case_name": "Z", "planned_date": "2026-04-10", "status": "overdue"}
        ]}}
        summary = await service.generate_summary_from_data(data)
        assert "PM 逾期" not in summary

    @pytest.mark.asyncio
    async def test_erp_expense_section_when_opted_in(self, service):
        """B2: erp_expense section opt-in。"""
        data = {
            "erp_pending_expenses": {
                "count": 2, "total_amount": 53000.0,
                "items": [
                    {"inv_num": "AB-12345678", "amount": 28000, "date": "2026-04-01",
                     "category": "設備", "status": "pending", "uploader": "王會計"},
                ],
            }
        }
        summary = await service.generate_summary_from_data(data, sections={"erp_expense"})
        assert "ERP 待審費用 2 筆" in summary
        assert "53,000" in summary

    @pytest.mark.asyncio
    async def test_missing_calendar_events_section(self, service):
        """遺漏建檔提醒格式正確（件號 + 主旨 + 天數）。"""
        data = {
            "missing_calendar_events": {
                "count": 1,
                "items": [
                    {
                        "doc_number": "府工程字第 11500012345 號",
                        "subject": "開會通知單 — Q2 工進檢討",
                        "category": "會議",
                        "days_ago": 3,
                    }
                ],
            }
        }
        summary = await service.generate_summary_from_data(data)
        assert "⚠️ 公文未建行事曆 1 件" in summary
        assert "府工程字第 11500012345 號" in summary
        assert "3 天" in summary
