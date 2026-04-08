"""AI 使用統計管理器 — re-export stub, actual code in core/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.core.ai_stats_manager")
_sys.modules[__name__] = _real
