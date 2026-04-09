"""AI 意圖解析規則引擎 — re-export stub, actual code in search/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.search.rule_engine")
_sys.modules[__name__] = _real
