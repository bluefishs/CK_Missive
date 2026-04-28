"""Wiki bounded context (DDD Wave 6, 2026-04-28).

Houses LLM Wiki authoring pipeline (Karpathy 4-Phase: Ingest/Compile/Query/Lint).

Public API:
    .compiler  — WikiCompiler (4-phase compile pipeline)
    .formatter — WikiFormatter (markdown formatting helpers)
    .service   — WikiService / get_wiki_service
    .coverage  — WikiCoverageService (KG↔Wiki audit)
"""
from .compiler import WikiCompiler  # noqa: F401
from .formatter import WikiFormatter  # noqa: F401
from .service import WikiService, get_wiki_service  # noqa: F401
from .coverage import WikiCoverageService  # noqa: F401
