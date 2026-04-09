"""Proactive Triggers PM 里程碑觸發掃描 — re-export stub, actual code in proactive/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.proactive.proactive_triggers_pm")
_sys.modules[__name__] = _real
