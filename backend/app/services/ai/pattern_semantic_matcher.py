"""Pattern Semantic Matcher — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.pattern_semantic_matcher")
_sys.modules[__name__] = _real
