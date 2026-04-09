"""案件全流程鏈追蹤器 — re-export stub, actual code in domain/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.domain.case_flow_tracker")
_sys.modules[__name__] = _real
