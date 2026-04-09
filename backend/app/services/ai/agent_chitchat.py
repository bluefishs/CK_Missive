"""Agent 閒聊偵測+回退模式 — re-export stub, actual code in agent/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.agent.agent_chitchat")
_sys.modules[__name__] = _real
