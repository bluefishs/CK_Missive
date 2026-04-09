"""Tool Registry 統一工具註冊中心 — re-export stub, actual code in tools/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.tools.tool_registry")
_sys.modules[__name__] = _real
