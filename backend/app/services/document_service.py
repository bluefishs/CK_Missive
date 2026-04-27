"""DDD Wave 1 sub-batch A migration shim — moved to services/document/core.py.

Migrated: 2026-04-27 (v5.9.9). Wave 1 100% — final batch.
See: docs/architecture/WAVE_1_SERVICES_MIGRATION_PLAYBOOK.md
"""
import warnings

warnings.warn(
    "services.document_service is deprecated; "
    "import from services.document.core (or services.document for DocumentService)",
    DeprecationWarning,
    stacklevel=2,
)

from .document.core import *  # noqa: F401,F403,E402
from .document.core import DocumentService  # noqa: F401,E402
