"""DDD Wave 1 sub-batch C migration shim — moved to services/notification/service.py.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.notification_service is deprecated; "
    "import from services.notification.service "
    "(or services.notification for NotificationService class only)",
    DeprecationWarning,
    stacklevel=2,
)

from .notification.service import *  # noqa: F401,F403,E402
from .notification.service import (  # noqa: F401,E402
    NotificationService,
    NotificationType,
    NotificationSeverity,
    CRITICAL_FIELDS,
)
