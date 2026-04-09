"""Agent 進化持久化 (DB history/graduations/push) — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_evolution_persistence")
_sys.modules[__name__] = _real
