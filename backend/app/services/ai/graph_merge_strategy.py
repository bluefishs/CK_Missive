"""圖譜實體合併策略 — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.graph_merge_strategy")
_sys.modules[__name__] = _real
