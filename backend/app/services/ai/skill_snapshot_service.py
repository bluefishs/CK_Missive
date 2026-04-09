"""Skill Snapshot Service — Git-based versioning for agent skills — re-export stub, actual code in misc/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.misc.skill_snapshot_service")
_sys.modules[__name__] = _real
