"""DDD Wave 4 migration shim — moved to services/tender/data_transformer.py."""
import warnings
warnings.warn("services.tender_data_transformer is deprecated; import from services.tender.data_transformer",
              DeprecationWarning, stacklevel=2)
from .tender.data_transformer import *  # noqa: F401,F403,E402
from .tender.data_transformer import (  # noqa: F401,E402
    dedup_records,
    normalize_record,
    normalize_detail,
    extract_award_details,
)
