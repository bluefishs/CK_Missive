"""DDD Wave 8 migration shim — moved to services/backup/auto_scheduler.py.

(renamed from backup_scheduler to avoid naming collision with backup/scheduler.py
which handles backup CRUD; auto_scheduler handles daily auto-backup + sync.)
"""
import warnings
warnings.warn("services.backup_scheduler is deprecated; import from services.backup.auto_scheduler",
              DeprecationWarning, stacklevel=2)
from .backup.auto_scheduler import *  # noqa: F401,F403,E402
from .backup.auto_scheduler import (  # noqa: F401,E402
    BackupScheduler,
    start_backup_scheduler,
    stop_backup_scheduler,
)
# get_backup_scheduler_status may exist
try:
    from .backup.auto_scheduler import get_backup_scheduler_status  # noqa: F401,E402
except ImportError:
    pass
