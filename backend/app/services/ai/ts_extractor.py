"""TypeScript / React 提取器 — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.ts_extractor")
_sys.modules[__name__] = _real
