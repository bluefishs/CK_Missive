"""Diff 影響分析服務 — re-export stub, actual code in misc/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.misc.diff_impact_analyzer")
_sys.modules[__name__] = _real
