"""System bounded context (DDD Wave 8, 2026-04-28).

Houses system-level health, monitoring, and observability concerns.

Public API:
    .health_service — SystemHealthService (main entry, includes uptime)
    .health_checks  — SystemHealthChecks (per-component checks)
"""
from .health_service import SystemHealthService, set_startup_time, get_uptime  # noqa: F401
from .health_checks import SystemHealthChecks  # noqa: F401
