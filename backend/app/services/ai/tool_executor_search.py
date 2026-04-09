"""搜尋類工具執行器 — re-export stub, actual code in tools/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.tools.tool_executor_search")
_sys.modules[__name__] = _real
