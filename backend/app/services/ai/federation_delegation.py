"""Federation Delegation -- 跨域委派模組 — re-export stub, actual code in federation/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.federation.federation_delegation")
_sys.modules[__name__] = _real
