"""圖譜查詢服務 — re-export stub, actual code in graph/"""
# Use sys.modules trick to make this stub transparently delegate to the real module.
# This ensures mock.patch("app.services.ai.graph_query_service.X") works correctly.
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.graph.graph_query_service")
_sys.modules[__name__] = _real
