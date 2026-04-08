"""關聯圖譜 & 語意相似推薦 Service — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.relation_graph_service")
_sys.modules[__name__] = _real
