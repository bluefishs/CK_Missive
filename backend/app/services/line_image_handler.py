"""DDD Wave 3 migration shim — moved to services/integration/line_image_handler.py.

Note: function-based module (download_line_content / analyze_image_with_vision / ...).
"""
import warnings

warnings.warn(
    "services.line_image_handler is deprecated; import from services.integration.line_image_handler",
    DeprecationWarning, stacklevel=2,
)

from .integration.line_image_handler import *  # noqa: F401,F403,E402
from .integration.line_image_handler import (  # noqa: F401,E402
    download_line_content,
    analyze_image_with_vision,
    try_create_expense_from_ocr,
)
