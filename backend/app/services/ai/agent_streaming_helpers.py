"""Agent 串流輔助模組 — 閒聊/非核心串流路徑 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_streaming_helpers")
_sys.modules[__name__] = _real
