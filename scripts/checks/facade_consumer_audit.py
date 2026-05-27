#!/usr/bin/env python3
"""facade_consumer_audit.py — fitness step 39

偵測 v6.10 P1 抽象層（contracts/facades/ + contracts/ports/）的零 caller 反模式。

背景：
    v6.10 P1 投入 24 .py（12 Facade + 4 Port + 4 Adapter + 4 ...）建抽象層，
    但 RETRO_20260519 §2.1 揭發 9/12 facade zero caller，4/4 port 只 1 個 caller。
    抽象建好沒人 call = build-without-consumer 反模式 = 浪費投資 + 製造未來 drift。

    2026-05-22 揭發具體 case：scheduler.py 5 個月 silent fail，因為它沒走 facade，
    而是 import 不存在的 line_bot.push_admin_alert（facade 同名 method 真實有實作）。

判定邏輯：
    1. 掃 backend/app/services/contracts/facades/*.py 取所有 public method (async def XXX)
    2. 掃 backend/app/ 找每個 method 的 callers（pattern: `Facade(...).method(` 或 `from ... import Facade; ...method(`）
    3. 每個 method 若 caller 數 == 0 → YELLOW warning（連續 14 天 → RED；待 v6.12 加 history）
    4. 跨 facade 統計：zero_caller_count / total_methods → ratio

Usage:
    python scripts/checks/facade_consumer_audit.py [--strict] [--detail]

Exit codes:
    0 = green (all facades have caller)
    1 = yellow (some zero callers; default not fail)
    2 = red (--strict mode and any zero caller)
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FACADE_DIR = REPO_ROOT / "backend" / "app" / "services" / "contracts" / "facades"
SCAN_ROOT = REPO_ROOT / "backend" / "app"

# 排除 facade 自身定義檔 + contracts/ 內部測試
EXCLUDE_PATHS = {
    "services/contracts/facades",
    "services/contracts/ports",
    "services/contracts/adapters",
    "__pycache__",
    "tests/contracts",  # facade 自身 test 不算 production caller
}

# 取 facade public method: `async def xxx(` (不含 _private)
METHOD_PATTERN = re.compile(r"^\s+async def ([a-z][a-z0-9_]*)\(", re.MULTILINE)
# Facade class name: `class XxxFacade:`
FACADE_CLASS_PATTERN = re.compile(r"^class (\w+Facade)", re.MULTILINE)


@dataclass
class FacadeMethod:
    facade_name: str       # e.g. IntegrationFacade
    method_name: str       # e.g. push_admin_alert
    source_file: Path      # facade 定義檔
    callers: list[Path] = field(default_factory=list)


@dataclass
class AuditResult:
    methods: list[FacadeMethod] = field(default_factory=list)
    zero_caller_methods: list[FacadeMethod] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = "unknown"


def _parse_facade(facade_file: Path) -> list[FacadeMethod]:
    """從一個 facade .py 取所有 public method。"""
    try:
        text = facade_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    classes = FACADE_CLASS_PATTERN.findall(text)
    if not classes:
        return []
    facade_name = classes[0]  # 預設一檔一 facade class
    methods = METHOD_PATTERN.findall(text)
    return [
        FacadeMethod(facade_name=facade_name, method_name=m, source_file=facade_file)
        for m in methods
    ]


def _scan_callers(method: FacadeMethod, all_py: list[Path]) -> list[Path]:
    """掃 backend/app/ 找 method caller。

    Heuristic：抓 `.method_name(` pattern 且檔案 import 了該 Facade。
    會有 false positive（同名 method 在別 class）但對 audit 目的足夠精準。
    """
    callers: list[Path] = []
    # 1. import 該 facade 的檔案
    facade_import_re = re.compile(
        rf"from app\.services\.contracts\.facades\..+ import .*{method.facade_name}",
    )
    method_call_re = re.compile(rf"\.{re.escape(method.method_name)}\(")
    for py in all_py:
        if py == method.source_file:
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # 要同時 import facade + call method 才算
        if not facade_import_re.search(text):
            continue
        if not method_call_re.search(text):
            continue
        callers.append(py)
    return callers


def _list_py_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*.py"):
        rel = p.relative_to(root).as_posix()
        if any(ex in rel for ex in EXCLUDE_PATHS):
            continue
        files.append(p)
    return files


def audit() -> AuditResult:
    result = AuditResult()
    if not FACADE_DIR.exists():
        result.warnings.append(f"⚠️  Facade dir missing: {FACADE_DIR}")
        result.status = "yellow"
        return result
    # 1. 取所有 facade method
    for facade_file in sorted(FACADE_DIR.glob("*.py")):
        if facade_file.name == "__init__.py":
            continue
        result.methods.extend(_parse_facade(facade_file))

    # 2. 掃 caller
    all_py = _list_py_files(SCAN_ROOT)
    for m in result.methods:
        m.callers = _scan_callers(m, all_py)
        if not m.callers:
            result.zero_caller_methods.append(m)

    # 3. 評估
    if result.zero_caller_methods:
        result.warnings.append(
            f"⚠️  {len(result.zero_caller_methods)}/{len(result.methods)} facade methods have ZERO caller"
        )
        result.status = "yellow"
    else:
        result.status = "green"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="Exit 2 if any zero-caller method exists")
    parser.add_argument("--detail", action="store_true",
                        help="Print each zero-caller method with its facade")
    args = parser.parse_args()

    print("🔍 facade_consumer_audit — v6.10 P1 抽象層 caller 真活檢查\n")
    result = audit()
    emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(result.status, "❓")
    print(f"{emoji} Status: {result.status.upper()}")
    print(f"  total facade methods:    {len(result.methods)}")
    print(f"  zero-caller methods:     {len(result.zero_caller_methods)}")
    callable_count = len(result.methods) - len(result.zero_caller_methods)
    if result.methods:
        pct = 100 * callable_count / len(result.methods)
        print(f"  utilization rate:        {callable_count}/{len(result.methods)} ({pct:.1f}%)")
    print()

    # By facade summary
    by_facade: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for m in result.methods:
        total, alive = by_facade[m.facade_name]
        by_facade[m.facade_name] = (total + 1, alive + (1 if m.callers else 0))
    print("  📊 Per-facade breakdown:")
    for fname, (total, alive) in sorted(by_facade.items()):
        bar = "✓" * alive + "✗" * (total - alive)
        marker = " ⚠️" if alive == 0 else ""
        print(f"    {fname:30s} {alive}/{total} {bar}{marker}")
    print()

    for w in result.warnings:
        print(f"  {w}")

    if args.detail and result.zero_caller_methods:
        print("\n  📋 Zero-caller methods (consider migrate caller to facade OR archive method):")
        for m in result.zero_caller_methods:
            print(f"    - {m.facade_name}.{m.method_name}() in {m.source_file.name}")

    if result.zero_caller_methods:
        print("\n💡 修法建議:")
        print("   1. 找 facade 對應的舊 import path（如 scheduler.py 用 line_bot.push_admin_alert）")
        print("   2. 改用 facade.method() 取代 → 自動成為 1 caller")
        print("   3. 若 facade 是 future-only abstraction，明確標 @experimental + 計時 14 天觀察")
        print("   範例: commit 75106542 — scheduler.py 改走 IntegrationFacade.push_admin_alert\n")

    if args.strict and result.zero_caller_methods:
        return 2
    if result.status == "yellow":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
