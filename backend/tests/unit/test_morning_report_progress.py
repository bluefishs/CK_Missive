# -*- coding: utf-8 -*-
"""_format_dispatch_progress + delivery helper 純函數測試 (Phase A5)"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.services.ai.domain.morning_report_service import MorningReportService


@pytest.fixture
def svc():
    return MorningReportService(MagicMock())


class TestFormatDispatchProgress:
    """_format_dispatch_progress 組合 stage_map × status_map × 公文對照"""

    def test_all_closed_excluded_upstream_but_format_still_works(self, svc):
        """雖上游 SQL 已排除嚴格結案，但 formatter 仍需能渲染 closed/completed 以防下游誤用。"""
        s = svc._format_dispatch_progress("closed", None, "completed", True, True)
        assert "已結案" in s
        assert "完成" in s
        assert "已對應發文" in s

    def test_survey_in_progress_with_only_incoming(self, svc):
        s = svc._format_dispatch_progress("survey", None, "in_progress", True, False)
        assert "查估" in s
        assert "進行中" in s
        assert "僅有來文" in s

    def test_meeting_notice_category_fallback(self, svc):
        """無 milestone_type 時 fallback 到 work_category 對照表。"""
        s = svc._format_dispatch_progress(None, "meeting_notice", "pending", False, False)
        assert "會議通知" in s
        assert "待辦" in s
        assert "無公文對照" in s

    def test_unknown_milestone_fallback_to_processing(self, svc):
        s = svc._format_dispatch_progress("mysterious_code", None, "on_hold", False, True)
        assert "處理中" in s
        assert "暫緩" in s
        assert "已對應發文" in s

    def test_no_record_no_doc(self, svc):
        s = svc._format_dispatch_progress(None, None, None, False, False)
        assert "無作業紀錄" in s
        assert "無公文對照" in s

    def test_outgoing_trumps_incoming_label(self, svc):
        """has_out=True 優先標示「已對應發文」而非「僅有來文」。"""
        s = svc._format_dispatch_progress("survey", None, "completed", True, True)
        assert "已對應發文" in s
        assert "僅有來文" not in s

    def test_status_empty_string_does_not_crash(self, svc):
        s = svc._format_dispatch_progress("survey", None, "", False, False)
        assert "查估" in s
        # empty status 不輸出狀態後綴，但不應炸

    @pytest.mark.parametrize("milestone,expected", [
        ("final_approval", "最終驗收完成"),
        ("submit_result", "提送成果"),
        ("review_meeting", "審查會議"),
        ("negotiation", "協商中"),
        ("boundary_survey", "界址測量"),
        ("revision", "修正中"),
        ("dispatch", "派工通知"),
    ])
    def test_all_milestone_mappings(self, svc, milestone, expected):
        s = svc._format_dispatch_progress(milestone, None, "in_progress", False, False)
        assert expected in s


class TestParseRocDate:
    """_parse_roc_date 民國年轉西元 — 晨報截止日判定的關鍵"""

    def test_standard_format(self, svc):
        assert svc._parse_roc_date("115年04月16日") == date(2026, 4, 16)

    def test_slash_separator(self, svc):
        assert svc._parse_roc_date("115/04/16") == date(2026, 4, 16)

    def test_two_digit_year(self, svc):
        # 99 年 = 2010
        assert svc._parse_roc_date("99年12月31日") == date(2010, 12, 31)

    def test_invalid_returns_none(self, svc):
        assert svc._parse_roc_date("not a date") is None
        assert svc._parse_roc_date("") is None
        assert svc._parse_roc_date(None) is None

    def test_invalid_month_returns_none(self, svc):
        # 13 月 — datetime 應拋例外被 catch
        assert svc._parse_roc_date("115年13月01日") is None


class TestTimezoneUsage:
    """A3 時區顯式 — 確保 _now_taipei 正常運作。"""

    def test_now_taipei_returns_aware_datetime(self):
        from app.services.ai.domain.morning_report_service import _now_taipei, TZ_TAIPEI
        now = _now_taipei()
        assert now.tzinfo is not None
        assert now.tzinfo == TZ_TAIPEI

    def test_today_taipei_in_delivery_helper(self):
        from app.services.ai.domain.morning_report_delivery import today_taipei
        d = today_taipei()
        assert isinstance(d, date)
