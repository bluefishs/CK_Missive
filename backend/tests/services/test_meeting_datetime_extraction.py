"""A (2026-06-11): 開會通知單「真實開會時間」抽取 + C 弱關鍵字 meeting 降級 regression。

對應 owner a+b+c 決議：
- A 會議事件抽取真實時段 → all_day=False（保留時間）；抽不到維持單日全天訖點。
- C 偶然提及會議(無 doc_type 佐證 + 無時間) → 不誤掛 [會議]/high。
"""
from datetime import datetime
from types import SimpleNamespace

from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder


def _builder():
    # _extract_meeting_datetime 僅用 document.subject，db 不被觸及
    return CalendarEventAutoBuilder(db=None)


def _doc(subject=None, doc_type=None, category=None):
    return SimpleNamespace(subject=subject, doc_type=doc_type, category=category)


class TestMeetingDatetimeExtraction:
    def test_roc_date_with_afternoon_time(self):
        b = _builder()
        assert b._extract_meeting_datetime(
            _doc("...契約變更協議會議112.11.16(四)下午2時")
        ) == datetime(2023, 11, 16, 14, 0)

    def test_roc_date_with_afternoon_hour_minute(self):
        b = _builder()
        assert b._extract_meeting_datetime(
            _doc("點交作業112.9.22(五)上午9時30分")
        ) == datetime(2023, 9, 22, 9, 30)

    def test_date_only_returns_none(self):
        # 只有日期、無時間 → None（維持單日全天）
        assert _builder()._extract_meeting_datetime(_doc("訂於112.9.21辦理")) is None

    def test_no_date_returns_none(self):
        assert _builder()._extract_meeting_datetime(_doc("取得會議(第4場)")) is None

    def test_month_only_no_full_date_returns_none(self):
        assert _builder()._extract_meeting_datetime(_doc("114年10月份安全衛生會議")) is None

    def test_noon_am_edge(self):
        # 上午12時 → 0 時
        assert _builder()._extract_meeting_datetime(
            _doc("113.5.6 上午12時")
        ) == datetime(2024, 5, 6, 0, 0)

    def test_invalid_month_rejected(self):
        assert _builder()._extract_meeting_datetime(_doc("112.13.40 下午2時")) is None


class TestWeakMeetingKeywordPrecision:
    def test_doc_type_meeting_is_authoritative(self):
        b = _builder()
        # 開會通知單 = 權威 → meeting
        assert b._determine_event_type(_doc("某會議", doc_type="開會通知單")) == "meeting"

    def test_keyword_meeting_classified_meeting(self):
        b = _builder()
        # 純關鍵字仍判 meeting（降級邏輯在 auto_create_event，依 doc_type + 時間佐證）
        assert b._determine_event_type(_doc("辦理開會事宜", category="收文")) == "meeting"
