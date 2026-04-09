"""Agent 自動進化排程 (50次/24h) — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_evolution_scheduler")
_sys.modules[__name__] = _real
