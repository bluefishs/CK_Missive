"""Pattern Semantic Matcher — 模式語意匹配 — re-export stub, actual code in misc/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.misc.pattern_semantic_matcher")
_sys.modules[__name__] = _real
