"""DDD Wave 2 migration shim — moved to services/erp/invoice_ocr_service.py."""
import warnings

warnings.warn(
    "services.invoice_ocr_service is deprecated; import from services.erp.invoice_ocr_service",
    DeprecationWarning, stacklevel=2,
)

from .erp.invoice_ocr_service import *  # noqa: F401,F403,E402
from .erp.invoice_ocr_service import (  # noqa: F401,E402
    InvoiceOCRService,
    InvoiceOCRResult,
)
