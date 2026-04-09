"""ERP Query Service — 企業資源 Agent 工具查詢服務 — re-export stub, actual code in domain/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.domain.erp_query_service")
_sys.modules[__name__] = _real
