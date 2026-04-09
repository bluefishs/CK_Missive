"""Agent 跨會話學習注入 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_learning_injector")
_sys.modules[__name__] = _real
