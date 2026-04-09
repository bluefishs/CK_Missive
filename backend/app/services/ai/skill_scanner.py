"""Skill 自動掃描器 — NemoClaw Stage 3 — re-export stub, actual code in misc/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.misc.skill_scanner")
_sys.modules[__name__] = _real
