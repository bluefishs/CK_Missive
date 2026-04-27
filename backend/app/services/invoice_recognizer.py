"""DDD Wave 2 migration shim — moved to services/erp/invoice_recognizer.py.

Note: this module exports dataclasses (InvoiceItem, RecognitionResult) and
function-based parsers (_parse_head_qr, _parse_detail_qr, _scan_all_qr).
"""
import warnings

warnings.warn(
    "services.invoice_recognizer is deprecated; import from services.erp.invoice_recognizer",
    DeprecationWarning, stacklevel=2,
)

from .erp.invoice_recognizer import *  # noqa: F401,F403,E402
from .erp.invoice_recognizer import (  # noqa: F401,E402
    InvoiceItem,
    RecognitionResult,
    _parse_head_qr,
    _parse_detail_qr,
    _scan_all_qr,
)
