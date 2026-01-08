# -*- coding: utf-8 -*-
"""
行事曆服務模組

提供行事曆事件管理、提醒處理、自動建立等功能。
"""
from app.services.calendar.event_auto_builder import (
    CalendarEventAutoBuilder,
    create_event_for_document,
)
from app.services.calendar.batch_create_events import (
    batch_create_calendar_events,
    get_calendar_statistics,
)

__all__ = [
    'CalendarEventAutoBuilder',
    'create_event_for_document',
    'batch_create_calendar_events',
    'get_calendar_statistics',
]
