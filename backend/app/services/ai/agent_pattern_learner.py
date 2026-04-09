"""Agent 查詢模式學習+MD5匹配 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_pattern_learner")
_sys.modules[__name__] = _real
