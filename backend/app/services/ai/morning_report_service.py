"""Morning Report Service — 每日晨報自動生成 + 推送 — re-export stub, actual code in domain/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.domain.morning_report_service")
_sys.modules[__name__] = _real
