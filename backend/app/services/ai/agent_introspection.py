"""Agent 自感知運行時 + Redis快取 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_introspection")
_sys.modules[__name__] = _real
