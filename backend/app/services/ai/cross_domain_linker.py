"""跨專案實體自動連結服務 — re-export stub, actual code in domain/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.domain.cross_domain_linker")
_sys.modules[__name__] = _real
