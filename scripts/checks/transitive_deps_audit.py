#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 34 - Transitive Deps Audit (v6.10 P1, 2026-05-18, LR-015 配套).

偵測 shared-modules/{pkg}/ 內每個 .py / .ts / .tsx 的 import 是否都「self-contained」
（在同 package 內、ck-* sibling、或框架白名單）。

依據 LR-015 諷刺對齊事件（2026-05-18 ck-navigation v1.0 半接通）：
真模組化原則 Rule 7：Self-Contained Imports — package 內 import 不出 package
（除 ck-* siblings 或框架白名單）。

對應 PACKAGING_PATTERN.md Rule 7。

Usage:
  python scripts/checks/transitive_deps_audit.py shared-modules/ck-navigation/
  python scripts/checks/transitive_deps_audit.py --ci   # strict
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHARED_MODULES = PROJECT_ROOT / "shared-modules"

# 框架白名單（合法外部 import）
FRAMEWORK_WHITELIST = {
    # Python
    "fastapi", "sqlalchemy", "pydantic", "redis", "asyncpg", "jose", "passlib",
    "httpx", "structlog", "prometheus_client", "apscheduler",
    "typing", "datetime", "pathlib", "json", "os", "sys", "re", "abc",
    # JS/TS framework
    "react", "antd", "axios", "react-router-dom", "@tanstack",
    "@ant-design", "lodash", "dayjs",
}


def _is_external_pkg(import_path: str) -> bool:
    """判定 import 是否屬框架白名單"""
    for prefix in FRAMEWORK_WHITELIST:
        if import_path == prefix or import_path.startswith(prefix + "."):
            return True
        if import_path == prefix or import_path.startswith(prefix + "/"):
            return True
    return False


def _scan_python_imports(pkg_root: Path, py_file: Path) -> list[dict]:
    """偵測 Python 檔的 import — 排除 package 內、ck-* sibling、框架"""
    violations = []
    try:
        text = py_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    # from X import Y / import X
    py_import_re = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)
    for m in py_import_re.finditer(text):
        module = m.group(1) or m.group(2)
        # 相對 import (.foo / ..foo) — 同 package 內
        if module.startswith("."):
            continue
        # app.* import — package 外部
        if module.startswith("app."):
            # 判定是否能在 package 內找到對應
            # 例：app.services.contracts.facades → 跨 package（contracts 不在當前 pkg 內）
            line_no = text[: m.start()].count("\n") + 1
            violations.append({
                "file": str(py_file.relative_to(pkg_root)),
                "line": line_no,
                "import": module,
                "type": "package_external",
                "reason": "import 'app.*' suggests cross-package dependency",
            })
            continue
        # 框架白名單
        if _is_external_pkg(module):
            continue
        # 標準函式庫不報
        if module.split(".")[0] in ("typing", "datetime", "pathlib", "json", "os", "sys",
                                      "re", "abc", "collections", "functools", "logging",
                                      "argparse", "subprocess", "shutil", "time"):
            continue
        # 未知 → 標記
        line_no = text[: m.start()].count("\n") + 1
        violations.append({
            "file": str(py_file.relative_to(pkg_root)),
            "line": line_no,
            "import": module,
            "type": "unknown_external",
            "reason": "not in framework whitelist and not relative",
        })
    return violations


def _scan_ts_imports(pkg_root: Path, ts_file: Path) -> list[dict]:
    """偵測 TS/TSX 檔的 import"""
    violations = []
    try:
        text = ts_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    ts_import_re = re.compile(r"""(?:^|\n)\s*import\s+(?:[^"';]+\s+from\s+)?["']([^"']+)["']""")
    for m in ts_import_re.finditer(text):
        path = m.group(1)
        # 相對 import (./foo / ../foo) — 須驗證實際指向是否在 package 內
        if path.startswith("./") or path.startswith("../"):
            # 解析相對路徑
            resolved = (ts_file.parent / path).resolve()
            # 加 .ts/.tsx 後綴試試
            candidates = [resolved, resolved.with_suffix(".ts"),
                         resolved.with_suffix(".tsx"),
                         resolved / "index.ts", resolved / "index.tsx"]
            in_pkg = any(
                pkg_root in c.parents or c == pkg_root for c in candidates if c.exists()
            )
            if not in_pkg:
                line_no = text[: m.start()].count("\n") + 1
                violations.append({
                    "file": str(ts_file.relative_to(pkg_root)),
                    "line": line_no,
                    "import": path,
                    "type": "relative_out_of_package",
                    "reason": f"resolves outside {pkg_root.name}",
                })
            continue
        # 框架白名單
        if _is_external_pkg(path):
            continue
        # 其他 (e.g., absolute non-framework) → 標記
        line_no = text[: m.start()].count("\n") + 1
        violations.append({
            "file": str(ts_file.relative_to(pkg_root)),
            "line": line_no,
            "import": path,
            "type": "unknown_external",
            "reason": "not in framework whitelist and not relative-internal",
        })
    return violations


def audit_package(pkg_path: Path) -> dict:
    """主審計流程"""
    if not pkg_path.exists():
        return {"error": f"path not found: {pkg_path}"}
    all_violations = []
    files_scanned = 0
    for f in pkg_path.rglob("*"):
        if "__pycache__" in f.parts or "node_modules" in f.parts:
            continue
        if not f.is_file():
            continue
        if f.suffix == ".py":
            files_scanned += 1
            all_violations.extend(_scan_python_imports(pkg_path, f))
        elif f.suffix in (".ts", ".tsx"):
            files_scanned += 1
            all_violations.extend(_scan_ts_imports(pkg_path, f))
    return {
        "package": str(pkg_path.relative_to(PROJECT_ROOT)) if PROJECT_ROOT in pkg_path.parents else str(pkg_path),
        "files_scanned": files_scanned,
        "violations": all_violations,
        "total": len(all_violations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 34 - Transitive Deps Audit (LR-015)")
    parser.add_argument("target", nargs="?", default=None,
                        help="package path (default: scan all shared-modules/)")
    parser.add_argument("--ci", action="store_true", help="strict mode")
    args = parser.parse_args()

    targets = []
    if args.target:
        targets = [Path(args.target).resolve()]
    else:
        if SHARED_MODULES.exists():
            targets = [d for d in SHARED_MODULES.iterdir()
                       if d.is_dir() and d.name.startswith("ck-")]

    total_violations = 0
    for pkg in targets:
        report = audit_package(pkg)
        print("=" * 60)
        print(f"Transitive Deps Audit - {report.get('package', pkg.name)}")
        print("=" * 60)
        if "error" in report:
            print(f"  [ERR] {report['error']}")
            continue
        print(f"  Files scanned: {report['files_scanned']}")
        print(f"  Total violations: {report['total']}")
        total_violations += report["total"]

        if report["violations"]:
            by_type = defaultdict(int)
            for v in report["violations"]:
                by_type[v["type"]] += 1
            print(f"\n  By type:")
            for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
                print(f"    {t:<30} {count}")
            print(f"\n  Sample violations (first 8):")
            for v in report["violations"][:8]:
                print(f"    L{v['line']:<5} {v['file']:<55} [{v['type']}]")
                print(f"            import: {v['import']}")
        print("")

    print("=" * 60)
    print(f"TOTAL ACROSS ALL PACKAGES: {total_violations}")
    print("=" * 60)

    if args.ci and total_violations > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
