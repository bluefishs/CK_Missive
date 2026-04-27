"""DDD Wave 1 sub-batch A migration shim — moved to services/document/receiver_normalizer.py.

Note: this module exports functions (normalize_unit, cc_list_to_json, ...) and
a NormalizedResult dataclass — not a service class.
"""
import warnings

warnings.warn(
    "services.receiver_normalizer is deprecated; "
    "import from services.document.receiver_normalizer",
    DeprecationWarning,
    stacklevel=2,
)

from .document.receiver_normalizer import *  # noqa: F401,F403,E402
from .document.receiver_normalizer import (  # noqa: F401,E402
    NormalizedResult,
    normalize_unit,
    cc_list_to_json,
    infer_agency_from_doc_number,
)
