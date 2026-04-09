"""Tool Discovery 動態工具推薦 — re-export stub, actual code in tools/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.tools.tool_discovery")
_sys.modules[__name__] = _real
