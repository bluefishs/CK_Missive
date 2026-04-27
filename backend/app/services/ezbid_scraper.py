"""DDD Wave 4 migration shim — moved to services/tender/ezbid_scraper.py."""
import warnings
warnings.warn("services.ezbid_scraper is deprecated; import from services.tender.ezbid_scraper",
              DeprecationWarning, stacklevel=2)
from .tender.ezbid_scraper import *  # noqa: F401,F403,E402
from .tender.ezbid_scraper import EzbidScraper  # noqa: F401,E402
