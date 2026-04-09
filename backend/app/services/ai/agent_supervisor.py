"""Agent Supervisor — 多 Agent 協調編排 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_supervisor")
_sys.modules[__name__] = _real
