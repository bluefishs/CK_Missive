"""雙層使用者記憶 — 從對話中萃取使用者偏好 — re-export stub, actual code in misc/"""
import importlib as _importlib
import sys as _sys

_real = _importlib.import_module("app.services.ai.misc.user_preference_extractor")
_sys.modules[__name__] = _real
