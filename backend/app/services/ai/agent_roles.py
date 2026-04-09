"""乾坤智能體角色定義 — Agent Role Profiles — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_roles")
_sys.modules[__name__] = _real
