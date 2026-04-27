"""DDD Wave 4 migration shim — moved to services/tender/analytics_battle.py."""
import warnings
warnings.warn("services.tender_analytics_battle is deprecated; import from services.tender.analytics_battle",
              DeprecationWarning, stacklevel=2)
from .tender.analytics_battle import *  # noqa: F401,F403,E402
from .tender.analytics_battle import (  # noqa: F401,E402
    _parse_amount,
    battle_room,
    org_ecosystem,
)
