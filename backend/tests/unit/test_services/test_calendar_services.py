# -*- coding: utf-8 -*-
"""
行事曆服務單元測試

測試 CalendarEventAutoBuilder 的事件建立邏輯、類型判定、日期選擇。
使用 Mock 資料庫，不需要實際連線。

執行方式:
    pytest tests/unit/test_services/test_calendar_services.py -v
"""
import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession


# =========================================================================
# Mock 工廠
# =========================================================================

def make_mock_db() -> MagicMock:
    """建立標準 Mock DB session"""
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


def make_document(**overrides) -> MagicMock:
    """建立 Mock 公文物件"""
    doc = MagicMock()
    defaults = {
        "id": 1,
        "doc_number": "府工測字第1140001234號",
        "doc_type": "函",
        "subject": "關於測繪作業事宜",
        "category": "收文",
        "sender": "桃園市政府",
        "receiver": "乾坤測繪有限公司",
        "receive_date": date(2026, 1, 15),
        "doc_date": date(2026, 1, 10),
        "send_date": None,
        "created_at": datetime(2026, 1, 15, 10, 0, 0),
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(doc, k, v)
    return doc


# =========================================================================
# CalendarEventAutoBuilder 測試
# =========================================================================

class TestEventTypeDetection:
    """測試事件類型判定"""

    def test_doc_type_meeting_notice(self):
        """開會通知單 -> meeting"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_type="開會通知單", subject="一般事項")

        event_type = builder._determine_event_type(doc)
        assert event_type == "meeting"

    def test_doc_type_inspection_notice(self):
        """會勘通知單 -> meeting"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_type="會勘通知單")

        event_type = builder._determine_event_type(doc)
        assert event_type == "meeting"

    def test_subject_keyword_deadline(self):
        """主旨含「截止」-> deadline"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_type="函", subject="本案截止日期為115年3月1日")

        event_type = builder._determine_event_type(doc)
        assert event_type == "deadline"

    def test_subject_keyword_review(self):
        """主旨含「審查」-> review"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_type="函", subject="成果審查會議通知")

        # "審查" comes before "會議" in the dict, so "review" wins
        event_type = builder._determine_event_type(doc)
        assert event_type == "review"

    def test_subject_keyword_meeting(self):
        """主旨含「會議」-> meeting"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_type="函", subject="工程協調會議通知")

        event_type = builder._determine_event_type(doc)
        assert event_type == "meeting"

    def test_category_default_incoming(self):
        """收文類別預設 -> reminder"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_type="函", subject="一般通知", category="收文")

        event_type = builder._determine_event_type(doc)
        assert event_type == "reminder"

    def test_category_default_outgoing(self):
        """發文類別預設 -> reference"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_type="函", subject="一般通知", category="發文")

        event_type = builder._determine_event_type(doc)
        assert event_type == "reference"

    def test_no_category_fallback(self):
        """無類別時 -> reminder"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_type="函", subject="一般通知", category=None)

        event_type = builder._determine_event_type(doc)
        assert event_type == "reminder"

    def test_doc_type_priority_over_keyword(self):
        """公文類型優先於主旨關鍵字"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        # doc_type = 開會通知單, but subject has 截止
        doc = make_document(doc_type="開會通知單", subject="截止日期前的會議")

        event_type = builder._determine_event_type(doc)
        assert event_type == "meeting"  # doc_type wins


class TestEventDateDetermination:
    """測試事件日期選擇"""

    def test_receive_date_priority(self):
        """收文日期最優先"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(
            receive_date=date(2026, 1, 15),
            doc_date=date(2026, 1, 10),
            send_date=date(2026, 1, 12),
        )

        event_date = builder._determine_event_date(doc)
        assert event_date.date() == date(2026, 1, 15)

    def test_doc_date_when_no_receive(self):
        """無收文日期時使用公文日期"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(receive_date=None, doc_date=date(2026, 1, 10))

        event_date = builder._determine_event_date(doc)
        assert event_date.date() == date(2026, 1, 10)

    def test_send_date_when_no_receive_or_doc(self):
        """無收文/公文日期時使用發文日期"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(
            receive_date=None,
            doc_date=None,
            send_date=date(2026, 1, 12),
        )

        event_date = builder._determine_event_date(doc)
        assert event_date.date() == date(2026, 1, 12)

    def test_created_at_fallback(self):
        """所有日期都沒有時用 created_at"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        created = datetime(2026, 1, 15, 10, 0, 0)
        doc = make_document(
            receive_date=None, doc_date=None, send_date=None,
            created_at=created,
        )

        event_date = builder._determine_event_date(doc)
        assert event_date == created

    def test_no_date_returns_none(self):
        """所有日期欄位都為 None 時回傳 None"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(
            receive_date=None, doc_date=None, send_date=None, created_at=None,
        )

        event_date = builder._determine_event_date(doc)
        assert event_date is None


class TestBuildTitle:
    """測試事件標題建構"""

    def test_deadline_prefix(self):
        """deadline 類型加上 [截止] 前綴"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(subject="本案成果繳交")

        title = builder._build_title(doc, "deadline")
        assert title.startswith("[截止]")
        assert "本案成果繳交" in title

    def test_meeting_prefix(self):
        """meeting 類型加上 [會議] 前綴"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(subject="工程協調會")

        title = builder._build_title(doc, "meeting")
        assert title.startswith("[會議]")

    def test_long_subject_truncation(self):
        """超長主旨截斷至 100 字"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(subject="A" * 200)

        title = builder._build_title(doc, "reminder")
        # prefix "[提醒] " + 100 chars + "..."
        assert len(title) <= 120

    def test_empty_subject(self):
        """無主旨時顯示「無主旨」"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(subject=None)

        title = builder._build_title(doc, "reminder")
        assert "無主旨" in title


class TestBuildDescription:
    """測試事件描述建構"""

    def test_description_with_all_fields(self):
        """包含公文字號、類別、類型"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document()

        desc = builder._build_description(doc)
        assert "公文字號" in desc
        assert "類別: 收文" in desc
        assert "公文類型: 函" in desc

    def test_description_without_optional_fields(self):
        """缺少部分欄位時不報錯"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(doc_number=None, category=None, doc_type=None)

        desc = builder._build_description(doc)
        assert desc == ""


class TestAutoCreateEvent:
    """測試自動建立事件"""

    @pytest.mark.asyncio
    async def test_skip_null_document(self):
        """空公文回傳 None"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)

        result = await builder.auto_create_event(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_skip_document_without_id(self):
        """無 ID 的公文回傳 None"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        doc = make_document(id=None)

        result = await builder.auto_create_event(doc)
        assert result is None

    @pytest.mark.asyncio
    async def test_skip_if_exists(self):
        """已有事件時跳過"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)

        # Mock existing event via repository
        builder._calendar_repo = MagicMock()
        builder._calendar_repo.check_document_has_events = AsyncMock(return_value=True)

        doc = make_document()
        result = await builder.auto_create_event(doc, skip_if_exists=True)

        assert result is None
        assert builder.skipped_count == 1

    @pytest.mark.asyncio
    async def test_skip_when_no_date(self):
        """無有效日期時跳過"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)

        # Mock no existing event via repository
        builder._calendar_repo = MagicMock()
        builder._calendar_repo.check_document_has_events = AsyncMock(return_value=False)

        doc = make_document(
            receive_date=None, doc_date=None,
            send_date=None, created_at=None,
        )
        result = await builder.auto_create_event(doc, skip_if_exists=True)

        assert result is None
        assert builder.skipped_count == 1

    @pytest.mark.asyncio
    async def test_create_event_success(self):
        """成功建立事件"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)

        # Mock no existing event via repository
        builder._calendar_repo = MagicMock()
        builder._calendar_repo.check_document_has_events = AsyncMock(return_value=False)

        doc = make_document()
        event = await builder.auto_create_event(doc, skip_if_exists=True)

        assert event is not None
        assert event.document_id == 1
        assert builder.created_count == 1
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_priority_mapping(self):
        """事件類型對應正確優先級"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)

        assert builder.EVENT_TYPE_PRIORITY_MAP["deadline"] == "high"
        assert builder.EVENT_TYPE_PRIORITY_MAP["meeting"] == "high"
        assert builder.EVENT_TYPE_PRIORITY_MAP["review"] == "normal"
        assert builder.EVENT_TYPE_PRIORITY_MAP["reference"] == "low"


class TestBatchCreateEvents:
    """測試批次建立事件"""

    @pytest.mark.asyncio
    async def test_batch_create_empty_list(self):
        """空列表回傳正確統計"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)

        result = await builder.batch_create_events([])

        assert result["total"] == 0
        assert result["created"] == 0
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_batch_create_multiple(self):
        """批次建立多個事件"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)

        # Mock no existing events via repository
        builder._calendar_repo = MagicMock()
        builder._calendar_repo.check_document_has_events = AsyncMock(return_value=False)

        docs = [make_document(id=i) for i in range(1, 4)]
        result = await builder.batch_create_events(docs, skip_if_exists=True)

        assert result["total"] == 3
        assert result["created"] == 3
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_batch_create_with_skips(self):
        """批次建立含跳過的事件"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)

        # First doc has existing event, others don't
        call_count = 0

        async def mock_check(document_id):
            nonlocal call_count
            call_count += 1
            return call_count == 1  # first call returns True (exists)

        builder._calendar_repo = MagicMock()
        builder._calendar_repo.check_document_has_events = AsyncMock(side_effect=mock_check)

        docs = [make_document(id=i) for i in range(1, 4)]
        result = await builder.batch_create_events(docs, skip_if_exists=True)

        assert result["total"] == 3
        assert result["created"] == 2
        assert result["skipped"] == 1


class TestCounterReset:
    """測試計數器重置"""

    def test_reset_counters(self):
        """重置計數器歸零"""
        from app.services.calendar.event_auto_builder import CalendarEventAutoBuilder

        db = make_mock_db()
        builder = CalendarEventAutoBuilder(db)
        builder._created_count = 5
        builder._skipped_count = 3

        builder.reset_counters()

        assert builder.created_count == 0
        assert builder.skipped_count == 0
