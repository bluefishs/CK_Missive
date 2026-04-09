"""Proactive Triggers Finance 觸發掃描 — re-export stub, actual code in proactive/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.proactive.proactive_triggers_finance")
_sys.modules[__name__] = _real
