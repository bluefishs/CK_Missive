"""DDD Wave 4 migration shim — moved to services/tender/pcc_today_scraper.py."""
import warnings
warnings.warn("services.pcc_today_scraper is deprecated; import from services.tender.pcc_today_scraper",
              DeprecationWarning, stacklevel=2)
from .tender.pcc_today_scraper import *  # noqa: F401,F403,E402
from .tender.pcc_today_scraper import PccTodayScraper  # noqa: F401,E402
