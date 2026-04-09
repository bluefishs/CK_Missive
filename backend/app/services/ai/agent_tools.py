"""Agent 工具模組 — 工具定義與調度入口 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_tools")
_sys.modules[__name__] = _real
