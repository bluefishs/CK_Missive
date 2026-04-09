"""文件分段服務 — re-export stub, actual code in document/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.document.document_chunker")
_sys.modules[__name__] = _real
