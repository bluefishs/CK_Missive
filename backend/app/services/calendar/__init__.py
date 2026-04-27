# -*- coding: utf-8 -*-
"""
行事曆服務模組

提供行事曆事件管理、提醒處理、自動建立等功能。
"""
from .event_auto_builder import (
    CalendarEventAutoBuilder,
    create_event_for_document,
)
from .batch_create_events import (
    batch_create_calendar_events,
    get_calendar_statistics,
)
# Wave 5 (2026-04-28): expanded with document_calendar_* + reminder_*
from .document_integrator import DocumentCalendarIntegrator
from .document_service import DocumentCalendarService
from .google_sync import CalendarGoogleSync
from .reminder_scheduler import ReminderScheduler, get_reminder_scheduler
from .reminder_service import ReminderService

__all__ = [
    'CalendarEventAutoBuilder',
    'create_event_for_document',
    'batch_create_calendar_events',
    'get_calendar_statistics',
    'DocumentCalendarIntegrator',
    'DocumentCalendarService',
    'CalendarGoogleSync',
    'ReminderScheduler',
    'get_reminder_scheduler',
    'ReminderService',
]
