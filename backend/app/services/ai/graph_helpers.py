"""圖譜查詢工具函數 — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.graph_helpers")
_sys.modules[__name__] = _real
