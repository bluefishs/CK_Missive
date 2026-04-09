"""數位分身服務層 — 聚合多源自覺資料 — re-export stub, actual code in domain/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.domain.digital_twin_service")
_sys.modules[__name__] = _real
