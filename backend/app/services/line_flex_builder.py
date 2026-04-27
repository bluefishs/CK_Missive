"""DDD Wave 3 migration shim — moved to services/integration/line_flex_builder.py.

Note: function-based module (build_deadline_flex / build_agent_reply_flex / ...).
"""
import warnings

warnings.warn(
    "services.line_flex_builder is deprecated; import from services.integration.line_flex_builder",
    DeprecationWarning, stacklevel=2,
)

from .integration.line_flex_builder import *  # noqa: F401,F403,E402
from .integration.line_flex_builder import (  # noqa: F401,E402
    build_deadline_flex,
    build_agent_reply_flex,
    build_progress_report_flex,
)
