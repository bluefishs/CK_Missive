"""RAG 檢索與上下文建構模組 — re-export stub, actual code in search/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.search.rag_retrieval")
_sys.modules[__name__] = _real
