# Google Calendar 整合模組
#
# v2.0.0: 統一使用 DocumentCalendarEvent 模型
# 棄用 legacy CalendarEvent (app.models.calendar_event)

from .client import google_calendar_client, GoogleCalendarClient
from .document_sync import document_calendar_sync, DocumentCalendarSync

__all__ = [
    'google_calendar_client',
    'GoogleCalendarClient',
    'document_calendar_sync',
    'DocumentCalendarSync',
]
