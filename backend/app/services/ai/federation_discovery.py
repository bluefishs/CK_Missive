"""Federation Discovery -- 服務發現模組 — re-export stub, actual code in federation/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.federation.federation_discovery")
_sys.modules[__name__] = _real
