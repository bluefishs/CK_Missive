"""DDD Wave 2 migration shim — moved to services/erp/invoice_ocr_parser.py.

Note: this module exports functions (try_ocr, try_vision_ocr).
"""
import warnings

warnings.warn(
    "services.invoice_ocr_parser is deprecated; import from services.erp.invoice_ocr_parser",
    DeprecationWarning, stacklevel=2,
)

from .erp.invoice_ocr_parser import *  # noqa: F401,F403,E402
from .erp.invoice_ocr_parser import try_ocr, try_vision_ocr  # noqa: F401,E402
