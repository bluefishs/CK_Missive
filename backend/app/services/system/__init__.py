"""System bounded context (DDD Wave 8/9, 2026-04-28 / 2026-05-05).

Houses system-level health, monitoring, observability, admin, and
navigation-sync concerns.

Public API:
    .health_service   — SystemHealthService (main entry, includes uptime)
    .health_checks    — SystemHealthChecks (per-component checks)
    .admin            — AdminService (DDD Wave 9)
    .navigation_sync  — sync_navigation_defaults (DDD Wave 9)
"""
from .health_service import SystemHealthService, set_startup_time, get_uptime  # noqa: F401
from .health_checks import SystemHealthChecks  # noqa: F401
from .admin import AdminService  # noqa: F401
from .navigation_sync import sync_navigation_defaults  # noqa: F401
from .role_permissions_service import RolePermissionsService  # noqa: F401
