"""Agent 後處理模組 — 引用核實、學習、評分 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_post_processing")
_sys.modules[__name__] = _real
