"""檢索結果重排序服務 — re-export stub, actual code in search/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.search.reranker")
_sys.modules[__name__] = _real
