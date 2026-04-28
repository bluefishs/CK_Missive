"""DDD Wave 6 migration shim — moved to services/wiki/compiler.py."""
import warnings
warnings.warn("services.wiki_compiler is deprecated; import from services.wiki.compiler",
              DeprecationWarning, stacklevel=2)
from .wiki.compiler import *  # noqa: F401,F403,E402
from .wiki.compiler import WikiCompiler  # noqa: F401,E402
