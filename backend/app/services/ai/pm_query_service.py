"""PM Query Service — 專案管理 Agent 工具查詢服務 — re-export stub, actual code in domain/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.domain.pm_query_service")
_sys.modules[__name__] = _real
