"""自然語言公文搜尋服務 — re-export stub, actual code in search/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.search.document_natural_search")
_sys.modules[__name__] = _real
