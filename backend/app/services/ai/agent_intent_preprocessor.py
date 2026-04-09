"""Agent 意圖前處理模組 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_intent_preprocessor")
_sys.modules[__name__] = _real
