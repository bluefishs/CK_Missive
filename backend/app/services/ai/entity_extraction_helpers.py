"""實體提取驗證/解析輔助模組 — re-export stub, actual code in document/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.document.entity_extraction_helpers")
_sys.modules[__name__] = _real
