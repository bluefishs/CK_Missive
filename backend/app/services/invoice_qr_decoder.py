"""DDD Wave 2 migration shim — moved to services/erp/invoice_qr_decoder.py.

Note: this module exports functions (scan_all_qr, parse_head_qr, parse_detail_qr).
"""
import warnings

warnings.warn(
    "services.invoice_qr_decoder is deprecated; import from services.erp.invoice_qr_decoder",
    DeprecationWarning, stacklevel=2,
)

from .erp.invoice_qr_decoder import *  # noqa: F401,F403,E402
from .erp.invoice_qr_decoder import (  # noqa: F401,E402
    scan_all_qr,
    parse_head_qr,
    parse_detail_qr,
)
