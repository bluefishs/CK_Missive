"""Agent Tool Monitor — 工具成功率監控與自動降級 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_tool_monitor")
_sys.modules[__name__] = _real
