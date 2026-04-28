"""DDD Wave 6 migration shim — moved to services/wiki/formatter.py."""
import warnings
warnings.warn("services.wiki_formatter is deprecated; import from services.wiki.formatter",
              DeprecationWarning, stacklevel=2)
from .wiki.formatter import *  # noqa: F401,F403,E402
from .wiki.formatter import WikiFormatter  # noqa: F401,E402
