"""Pattern Learner Cold-Start Seed Data — re-export stub, actual code in misc/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.misc.pattern_seeds")
_sys.modules[__name__] = _real
