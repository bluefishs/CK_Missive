"""Agent 能力自覺模組 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_capability_tracker")
_sys.modules[__name__] = _real
