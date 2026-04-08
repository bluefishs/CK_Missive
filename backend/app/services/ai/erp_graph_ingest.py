"""ERP Graph 入圖服務 — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.erp_graph_ingest")
_sys.modules[__name__] = _real
