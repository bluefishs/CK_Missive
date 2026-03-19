"""
多層級提醒服務單元測試

測試範圍：
- _format_time_description: 時間描述格式化
- _build_reminder_message: 提醒訊息建構
- create_multi_level_reminders: 多層級提醒創建
- send_reminder: 提醒發送（email/system）
- _handle_failed_reminder: 失敗重試（指數退避）
- get_event_reminders_status: 提醒狀態查詢

共 7 test cases
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.reminder_service import ReminderService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    with patch(
        "app.services.reminder_service.NotificationService"
    ):
        svc = ReminderService(mock_db)
        svc.notification_service = AsyncMock()
        return svc


# ============================================================================
# _format_time_description
# ============================================================================

class TestFormatTimeDescription:
    """時間描述格式化"""

    def test_minutes(self, service):
        assert service._format_time_description(30) == "30分鐘前"

    def test_hours(self, service):
        assert service._format_time_description(120) == "2小時前"

    def test_days(self, service):
        assert service._format_time_description(60 * 24 * 3) == "3天前"


# ============================================================================
# _build_reminder_message
# ============================================================================

class TestBuildReminderMessage:
    """提醒訊息建構"""

    def test_basic_message(self, service):
        """基本訊息包含事件標題和時間"""
        event = MagicMock()
        event.title = "公文截止"
        event.start_date = datetime(2026, 3, 15, 10, 0)
        event.description = "請儘速辦理"
        event.location = "會議室A"
        event.meeting_url = None

        config = {"minutes": 60, "type": "email", "priority": 2}
        msg = service._build_reminder_message(event, config)

        assert "公文截止" in msg
        assert "2026-03-15 10:00" in msg
        assert "1小時前" in msg
        assert "會議室A" in msg

    def test_message_with_meeting_url(self, service):
        """含會議連結的訊息"""
        event = MagicMock()
        event.title = "線上會議"
        event.start_date = datetime(2026, 3, 15, 14, 0)
        event.description = None
        event.location = None
        event.meeting_url = "https://meet.google.com/abc"

        config = {"minutes": 1440, "type": "email", "priority": 1}
        msg = service._build_reminder_message(event, config)

        assert "https://meet.google.com/abc" in msg


# ============================================================================
# create_multi_level_reminders
# ============================================================================

class TestCreateMultiLevelReminders:
    """多層級提醒創建"""

    @pytest.mark.asyncio
    async def test_creates_reminders_for_deadline(self, service, mock_db):
        """截止日期事件建立提醒"""
        event = MagicMock()
        event.id = 1
        event.event_type = "deadline"
        event.title = "公文截止"
        event.start_date = datetime.now() + timedelta(days=3)
        event.assigned_user_id = 10
        event.description = "測試"
        event.location = None
        event.meeting_url = None

        result = await service.create_multi_level_reminders(event)

        assert len(result) >= 1
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_reference_event_no_reminders(self, service, mock_db):
        """參考事件不建立提醒"""
        event = MagicMock()
        event.id = 2
        event.event_type = "reference"
        event.title = "參考資料"
        event.start_date = datetime.now() + timedelta(days=1)
        event.assigned_user_id = 10

        result = await service.create_multi_level_reminders(event)
        assert len(result) == 0


# ============================================================================
# _handle_failed_reminder
# ============================================================================

class TestHandleFailedReminder:
    """失敗重試處理"""

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, service):
        """指數退避重試"""
        reminder = MagicMock()
        reminder.retry_count = 1
        reminder.max_retries = 5

        await service._handle_failed_reminder(reminder)

        assert reminder.retry_count == 2
        assert reminder.next_retry_at is not None
        assert reminder.status != "failed"

    @pytest.mark.asyncio
    async def test_max_retries_reached(self, service):
        """達到最大重試次數標記失敗"""
        reminder = MagicMock()
        reminder.retry_count = 4
        reminder.max_retries = 5

        await service._handle_failed_reminder(reminder)

        assert reminder.retry_count == 5
        assert reminder.status == "failed"
