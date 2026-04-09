"""AI 分析結果持久化服務 — re-export stub, actual code in document/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.document.document_analysis_service")
_sys.modules[__name__] = _real
