"""Agent 合成模組 — 答案合成、thinking 過濾、context 建構 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_synthesis")
_sys.modules[__name__] = _real
