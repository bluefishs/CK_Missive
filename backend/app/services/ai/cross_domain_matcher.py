"""跨域實體匹配引擎 — re-export stub, actual code in domain/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.domain.cross_domain_matcher")
_sys.modules[__name__] = _real
