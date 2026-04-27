"""Agency bounded context (DDD Wave 1 sub-batch B, 2026-04-27).

Houses government agency + client (委託單位) management.

Public API:
    AgencyService              — agency CRUD
    AgencyMatchingService      — fuzzy/exact agency name matching
    AgencyStatisticsService    — agency-level statistics & aggregations
"""
from .core import AgencyService  # noqa: F401
from .matching import AgencyMatchingService  # noqa: F401
from .statistics import AgencyStatisticsService  # noqa: F401
