"""附件內容索引服務 — re-export stub, actual code in document/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.document.attachment_content_indexer")
_sys.modules[__name__] = _real
