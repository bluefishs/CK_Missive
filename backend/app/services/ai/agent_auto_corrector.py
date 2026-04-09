"""Agent 自動修正模組 (6策略) — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_auto_corrector")
_sys.modules[__name__] = _real
