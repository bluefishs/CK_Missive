"""Proactive Triggers 主動觸發通知服務 — re-export stub, actual code in proactive/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.proactive.proactive_triggers")
_sys.modules[__name__] = _real
