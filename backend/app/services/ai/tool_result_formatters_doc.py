"""工具結果格式化 公文/派工/統計 — re-export stub, actual code in tools/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.tools.tool_result_formatters_doc")
_sys.modules[__name__] = _real
