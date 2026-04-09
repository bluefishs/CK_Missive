"""Agent 規劃模組 — 意圖前處理、LLM 工具規劃、ReAct 循環 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_planner")
_sys.modules[__name__] = _real
