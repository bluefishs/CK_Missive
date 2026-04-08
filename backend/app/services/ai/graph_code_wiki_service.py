"""Code Wiki 圖譜服務 — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.graph_code_wiki_service")
_sys.modules[__name__] = _real
