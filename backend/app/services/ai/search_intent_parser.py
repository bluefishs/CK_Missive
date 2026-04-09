"""搜尋意圖解析器 — re-export stub, actual code in search/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.search.search_intent_parser")
_sys.modules[__name__] = _real
