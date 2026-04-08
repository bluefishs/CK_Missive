"""Domain-specific prompts — re-export stub, actual code in core/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.core.domain_prompts")
_sys.modules[__name__] = _real
