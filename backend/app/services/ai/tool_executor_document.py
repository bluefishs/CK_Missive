"""Document parsing tool executor — re-export stub, actual code in tools/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.tools.tool_executor_document")
_sys.modules[__name__] = _real
