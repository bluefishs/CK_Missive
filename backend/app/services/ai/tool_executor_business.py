"""業務工具執行器 (資產/費用/派工/風險/意圖) — re-export stub, actual code in tools/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.tools.tool_executor_business")
_sys.modules[__name__] = _real
