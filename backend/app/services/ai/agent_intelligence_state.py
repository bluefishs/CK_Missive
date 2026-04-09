"""Agent 統一智能體狀態中樞 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_intelligence_state")
_sys.modules[__name__] = _real
