"""AI 速率限制器 — re-export stub, actual code in core/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.core.ai_rate_limiter")
_sys.modules[__name__] = _real
