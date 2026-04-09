"""公文搜尋輔助函數 — re-export stub, actual code in document/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.document.document_search_helpers")
_sys.modules[__name__] = _real
