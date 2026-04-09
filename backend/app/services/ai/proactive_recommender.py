"""Proactive Recommender 主動推薦引擎 — re-export stub, actual code in proactive/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.proactive.proactive_recommender")
_sys.modules[__name__] = _real
