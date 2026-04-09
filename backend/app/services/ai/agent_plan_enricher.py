"""Agent 計劃充實器 — 合併 hints + 強制工具注入 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_plan_enricher")
_sys.modules[__name__] = _real
