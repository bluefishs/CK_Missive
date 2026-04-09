"""Agent 工具迴圈 — ReAct Loop + Chain-of-Tools — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_tool_loop")
_sys.modules[__name__] = _real
