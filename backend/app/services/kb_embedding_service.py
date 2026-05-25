"""DDD Wave 9 migration shim — moved to services/ai/misc/kb_embedding.py."""
import warnings
warnings.warn(
    "services.kb_embedding_service is deprecated; import from services.ai.misc.kb_embedding",
    DeprecationWarning, stacklevel=2,
)
from .ai.misc.kb_embedding import *  # noqa: F401,F403,E402
from .ai.misc.kb_embedding import KBEmbeddingService  # noqa: F401,E402
