"""DDD Wave 3 migration shim — moved to services/integration/agent_stream_helper.py."""
import warnings

warnings.warn(
    "services.agent_stream_helper is deprecated; import from services.integration.agent_stream_helper",
    DeprecationWarning, stacklevel=2,
)

from .integration.agent_stream_helper import *  # noqa: F401,F403,E402
from .integration.agent_stream_helper import (  # noqa: F401,E402
    StreamResult,
    AgentStreamCollector,
)
