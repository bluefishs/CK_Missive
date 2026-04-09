"""Agent Self-Evaluator — 每次回答自動評分 + 改進信號 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_self_evaluator")
_sys.modules[__name__] = _real
