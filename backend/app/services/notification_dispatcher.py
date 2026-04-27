"""DDD Wave 1 migration shim — moved to services/notification/dispatcher.py.

This stub re-exports the public API for backward compatibility.
Plan to remove after 2026-Q3 once all imports are updated to the new path.

Migrated: 2026-04-27 (v5.9.9)
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.notification_dispatcher is deprecated; "
    "import from services.notification.dispatcher (or services.notification)",
    DeprecationWarning,
    stacklevel=2,
)

from .notification.dispatcher import *  # noqa: F401,F403,E402
from .notification.dispatcher import (  # noqa: F401,E402
    NotificationDispatcher,
    NotificationChannel,
    NotificationTarget,
    Severity,
)
