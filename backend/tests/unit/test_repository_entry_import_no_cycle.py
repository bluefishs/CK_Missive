# -*- coding: utf-8 -*-
"""以 repository 為入口匯入不得循環（2026-09-09 晚）。

把 `from app.services.stats import finance` 放在 repository 模組層，app 啟動時因匯入順序不炸，
但腳本／測試以 repository 為第一個入口時：`app.services/__init__` → contract 服務 → `app.repositories`（初始化中）
→ 該 repository → `app.services`… ⇒ ImportError。修法＝`app/repositories/_fm.py` 延遲代理。
這條鎖用**新直譯器**驗，因為在本測試行程裡 app 早就載好了，看不到循環。
"""
import os
import subprocess
import sys

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

ENTRIES = [
    "app.repositories.vendor_repository",
    "app.repositories.erp.vendor_payable_repository",
    "app.repositories.erp.financial_summary_repository",
    "app.repositories.erp.client_receivable_repository",
    "app.repositories.erp.billing_repository",
]


@pytest.mark.parametrize("module", ENTRIES)
def test_fresh_interpreter_can_import_repository_first(module):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYGUARD_MAX_GB="2")
    r = subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {BACKEND!r}); import {module}; print('OK')"],
        capture_output=True, text=True, timeout=120, env=env, cwd=BACKEND,
    )
    assert r.returncode == 0 and "OK" in r.stdout, (r.stderr or "")[-600:]
