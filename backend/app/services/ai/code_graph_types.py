"""Code Graph 共用資料類別 — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.code_graph_types")
_sys.modules[__name__] = _real
