"""Agent Pattern Persistence — DB graduation + seed loading — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_pattern_persistence")
_sys.modules[__name__] = _real
