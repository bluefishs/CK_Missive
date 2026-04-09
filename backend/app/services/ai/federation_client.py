"""Federation Client -- 聯邦式 AI 系統間呼叫客戶端 — re-export stub, actual code in federation/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.federation.federation_client")
_sys.modules[__name__] = _real
