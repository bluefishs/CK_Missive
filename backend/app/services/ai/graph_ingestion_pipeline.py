"""知識圖譜入圖管線 — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.graph_ingestion_pipeline")
_sys.modules[__name__] = _real
