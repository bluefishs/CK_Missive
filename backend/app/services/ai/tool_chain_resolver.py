"""工具鏈參數解析器 — re-export stub, actual code in tools/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.tools.tool_chain_resolver")
_sys.modules[__name__] = _real
