"""Regression: 行事曆事件 start_date > end_date 顛倒防呆（2026-06-30）

根因：work_record_calendar_sync / document_sync 更新分支只改單側日期欄位，
導致 start>end 顛倒 → 完成判定看 end_date(過去)誤標完成、/calendar 月檢視
重疊查詢兩月皆不匹配而隱形、Google 同步日期錯。

防護：DocumentCalendarEvent before_insert/before_update 監聽器收斂 end>=start。
此測試鎖定該監聽器，避免日後重構移除後 silent 回歸。
"""
from datetime import datetime

from app.extended.models.calendar import (
    DocumentCalendarEvent,
    _normalize_calendar_event_dates,
)


def _make_event(start, end):
    ev = DocumentCalendarEvent(
        title="t",
        start_date=start,
        end_date=end,
        all_day=True,
        event_type="reminder",
    )
    # 直接呼叫監聽器（不需 DB session）模擬 before_insert/update
    _normalize_calendar_event_dates(None, None, ev)
    return ev


def test_inverted_dates_collapse_to_start():
    """end < start（顛倒）→ 收斂為 end = start。"""
    start = datetime(2026, 7, 9, 18, 0)
    end = datetime(2026, 6, 15, 12, 0)  # 早於 start，顛倒
    ev = _make_event(start, end)
    assert ev.start_date == start
    assert ev.end_date == start  # 收斂到未來 deadline 點
    assert ev.end_date >= ev.start_date


def test_valid_timed_range_unchanged():
    """正常 end > start（如 meeting 1hr）不被動到。"""
    start = datetime(2026, 7, 10, 9, 0)
    end = datetime(2026, 7, 10, 10, 0)
    ev = _make_event(start, end)
    assert ev.start_date == start
    assert ev.end_date == end  # 不變


def test_single_point_unchanged():
    """start == end（全天單點）不被動到。"""
    pt = datetime(2026, 7, 15, 12, 0)
    ev = _make_event(pt, pt)
    assert ev.start_date == pt
    assert ev.end_date == pt


def test_null_end_not_crash():
    """end_date 為 None 時不應 crash。"""
    start = datetime(2026, 7, 9, 18, 0)
    ev = _make_event(start, None)
    assert ev.start_date == start
    assert ev.end_date is None
