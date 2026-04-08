"""業務實體圖譜建構器 — re-export stub, actual code in graph/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.graph_business_entity_builder")
_sys.modules[__name__] = _real
