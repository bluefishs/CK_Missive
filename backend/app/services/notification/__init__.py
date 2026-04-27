"""Notification bounded context (DDD Wave 1, 2026-04-27).

Currently houses the unified multi-channel dispatcher.
Future migrations will move `services/notification_service.py` here as well.

Public API:
    NotificationDispatcher — multi-channel push (LINE/Discord/Telegram/...)
    NotificationChannel    — channel enum
    NotificationPayload    — payload dataclass
"""
from .dispatcher import *  # noqa: F401,F403
from .dispatcher import (  # noqa: F401  (explicit re-export for IDE)
    NotificationDispatcher,
    NotificationChannel,
    NotificationTarget,
    Severity,
)
