#!/usr/bin/env python3
"""
AI re-export stub 一致性驗證

檢查 backend/app/services/ai/*.py 中的 re-export stub 是否都指向有效模組。

Usage:
    python scripts/checks/verify_ai_stubs.py
"""
import os
import re
import sys

STUB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "app", "services", "ai")
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")


def verify_stubs():
    stub_dir = os.path.normpath(STUB_DIR)
    backend_dir = os.path.normpath(BACKEND_DIR)
    stubs = []
    errors = []

    for f in sorted(os.listdir(stub_dir)):
        if not f.endswith(".py") or f == "__init__.py":
            continue
        path = os.path.join(stub_dir, f)
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Detect re-export stub pattern: importlib.import_module("target")
        m = re.search(r'import_module\(["\']([^"\']+)["\']\)', content)
        if not m:
            continue

        target = m.group(1)
        stubs.append((f, target))

        # Verify target module file exists
        target_path = os.path.join(backend_dir, target.replace(".", os.sep) + ".py")
        if not os.path.exists(target_path):
            # Also check if it's a package (__init__.py)
            pkg_path = os.path.join(backend_dir, target.replace(".", os.sep), "__init__.py")
            if not os.path.exists(pkg_path):
                errors.append(f"  {f} -> {target} (MISSING)")

    print(f"AI re-export stubs: {len(stubs)} found")

    if errors:
        print(f"FAILED — {len(errors)} broken stubs:")
        for e in errors:
            print(e)
        return 1

    print("PASSED — all stubs point to valid targets")
    return 0


if __name__ == "__main__":
    sys.exit(verify_stubs())
