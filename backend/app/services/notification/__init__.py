"""Notification bounded context (DDD Wave 1 sub-batch C, 2026-04-27).

Houses unified multi-channel push (dispatcher) + in-app notifications (service)
+ helpers + template engine.

Public API (use specific submodule path for sub-types to avoid name
collisions — both `service` and `template` define `NotificationType`):

    .dispatcher  — NotificationDispatcher / NotificationChannel / Severity / NotificationTarget
    .service     — NotificationService / NotificationType / NotificationSeverity / CRITICAL_FIELDS
    .helpers     — safe_notify_critical_change / safe_notify_document_deleted / ...
    .template    — NotificationTemplateService / NotificationTemplate / NotificationPriority

For convenience this `__init__.py` re-exports only the three main service
classes; everything else should be imported from its specific submodule.
"""
from .dispatcher import NotificationDispatcher  # noqa: F401
from .service import NotificationService  # noqa: F401
from .template import NotificationTemplateService  # noqa: F401
