"""工具結果格式化 知識圖譜實體 — re-export stub, actual code in tools/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.tools.tool_result_formatters_entity")
_sys.modules[__name__] = _real
