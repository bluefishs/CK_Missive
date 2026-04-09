"""派工進度彙整合成服務 — re-export stub, actual code in domain/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.domain.dispatch_progress_synthesizer")
_sys.modules[__name__] = _real
