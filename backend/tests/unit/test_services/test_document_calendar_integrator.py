"""
公文行事曆整合器服務單元測試

測試範圍：
- parse_document_dates: 日期解析
- _build_event_description: 事件描述建構
- _determine_priority: 優先級決定
- _get_default_reminder_minutes: 預設提醒時間
- convert_document_to_events: 事件建立主流程
- get_document_events: 查詢公文事件

共 7 test cases
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.document_calendar_integrator import DocumentCalendarIntegrator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def integrator():
    with patch("app.services.document_calendar_integrator.DocumentCalendarService"), \
         patch("app.services.document_calendar_integrator.ProjectNotificationService"):
        return DocumentCalendarIntegrator()


@pytest.fixture
def mock_document():
    doc = MagicMock()
    doc.id = 1
    doc.subject = "道路改善工程"
    doc.doc_number = "桃工字第001號"
    doc.doc_date = date(2026, 3, 1)
    doc.receive_date = date(2026, 3, 2)
    doc.send_date = date(2026, 3, 10)
    doc.content = None
    return doc


# ============================================================================
# parse_document_dates
# ============================================================================

class TestParseDocumentDates:
    """日期解析測試"""

    def test_extracts_all_dates(self, integrator, mock_document):
        dates = integrator.parse_document_dates(mock_document)
        types = [d[0] for d in dates]
        assert "reference" in types  # doc_date
        assert "reminder" in types   # receive_date
        assert "deadline" in types   # send_date

    def test_no_dates_returns_empty(self, integrator):
        doc = MagicMock()
        doc.doc_date = None
        doc.receive_date = None
        doc.send_date = None
        doc.content = None
        dates = integrator.parse_document_dates(doc)
        assert dates == []

    def test_partial_dates(self, integrator):
        doc = MagicMock()
        doc.doc_date = date(2026, 1, 1)
        doc.receive_date = None
        doc.send_date = None
        doc.content = None
        dates = integrator.parse_document_dates(doc)
        assert len(dates) == 1
        assert dates[0][0] == "reference"


# ============================================================================
# _build_event_description
# ============================================================================

class TestBuildEventDescription:
    """事件描述建構測試"""

    def test_description_format(self, integrator, mock_document):
        desc = integrator._build_event_description(mock_document, "公文收文提醒")
        assert "公文收文提醒" in desc
        assert "桃工字第001號" in desc


# ============================================================================
# _determine_priority / _get_default_reminder_minutes
# ============================================================================

class TestPriorityAndReminder:
    """優先級與提醒時間測試"""

    def test_priority_returns_integer(self, integrator, mock_document):
        priority = integrator._determine_priority("deadline", mock_document)
        assert isinstance(priority, int)

    def test_reminder_minutes_returns_integer(self, integrator):
        minutes = integrator._get_default_reminder_minutes("deadline")
        assert isinstance(minutes, int)
        assert minutes > 0


# ============================================================================
# convert_document_to_events (async)
# ============================================================================

class TestConvertDocumentToEvents:
    """事件建立主流程測試"""

    @pytest.mark.asyncio
    async def test_creates_events_from_dates(self, integrator, mock_document):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        integrator.calendar_service.is_ready = MagicMock(return_value=False)

        mock_event = MagicMock()
        mock_event.id = 1

        with patch("app.services.document_calendar_integrator.DocumentCalendarEvent", return_value=mock_event) as MockEvent, \
             patch("app.services.document_calendar_integrator.ReminderService") as MockReminder:
            mock_reminder = AsyncMock()
            MockReminder.return_value = mock_reminder

            events = await integrator.convert_document_to_events(
                mock_db, mock_document
            )

        # Should create events for doc_date, receive_date, send_date
        assert len(events) == 3
        assert mock_db.add.call_count == 3
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_dates_returns_empty(self, integrator):
        doc = MagicMock()
        doc.id = 2
        doc.doc_date = None
        doc.receive_date = None
        doc.send_date = None
        doc.content = None

        mock_db = AsyncMock()
        events = await integrator.convert_document_to_events(mock_db, doc)
        assert events == []


# ============================================================================
# get_document_events (async)
# ============================================================================

class TestGetDocumentEvents:
    """查詢公文事件測試"""

    @pytest.mark.asyncio
    async def test_returns_events(self, integrator):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(), MagicMock()]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        events = await integrator.get_document_events(mock_db, document_id=1)
        assert len(events) == 2
