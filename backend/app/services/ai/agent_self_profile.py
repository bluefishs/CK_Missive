"""Agent Self-Profile — identity card builder — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_self_profile")
_sys.modules[__name__] = _real
