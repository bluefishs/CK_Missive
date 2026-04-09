"""User Query Graph -- per-user interest profiling — re-export stub, actual code in misc/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.misc.user_query_tracker")
_sys.modules[__name__] = _real
