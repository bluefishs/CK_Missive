#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: Dead Config Reader 偵測

STANDARD_REFERENCE.md §4 要求：yaml config 若無生產讀取點就是 dead config。

設計意圖：定義了 config getter/property 卻沒人呼叫 = 形同裝飾。
2026-04-24 ADR-0030 審計事件：get_preferred_providers / should_prefer_local 定義了
但生產 0 呼叫點，yaml provider_routing 形同 dead config → 誤導 5 輪 session。

掃描對象：
    backend/app/services/ai/core/ai_config.py 的 public property / method

用法：
    python scripts/checks/config_dead_reader_scan.py
    python scripts/checks/config_dead_reader_scan.py --ci     # CI mode
    python scripts/checks/config_dead_reader_scan.py --target backend/app/services/ai/core/ai_config.py

輸出：
    列出定義但 0 生產呼叫的 config getter（test 檔不算呼叫）

Version: 1.0.0 (2026-04-25)
關聯:
    - docs/architecture/STANDARD_REFERENCE.md §4
    - memory/baseline_quality_recovery_20260424.md (SSOT dead config 覆盤)
    - backend/tests/integration/test_ai_connector_yaml_routing_ssot.py (接線鎖定)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_TARGET = Path("backend/app/services/ai/core/ai_config.py")
PRODUCTION_ROOT = Path("backend/app")
# 排除的路徑（不算生產呼叫）
EXCLUDE_FRAGMENTS = ("/tests/", "/test_", "\\tests\\", "\\test_")
# Constructor patterns（透過 module-level factory 間接呼叫，scanner 無法追蹤）
CONSTRUCTOR_PATTERNS = {"from_env", "from_dict", "from_yaml", "create", "build"}


def find_public_methods_and_properties(target: Path) -> list[tuple[str, str]]:
    """從 target Python 檔找 public def / property
    Returns: [(name, kind)] where kind in {"method", "property"}
    """
    if not target.exists():
        print(f"ERROR: target {target} not found", file=sys.stderr)
        sys.exit(2)

    src = target.read_text(encoding="utf-8")
    results: list[tuple[str, str]] = []

    # 找 class 內的 def（粗略 AST — re-based 簡化）
    prop_next = False
    for line in src.splitlines():
        stripped = line.strip()
        if stripped == "@property":
            prop_next = True
            continue
        m = re.match(r"^\s+def\s+([a-zA-Z_]\w*)\s*\(", line)
        if m:
            name = m.group(1)
            if not name.startswith("_"):
                kind = "property" if prop_next else "method"
                results.append((name, kind))
            prop_next = False
            continue
        # 非 def 行且不是空白/裝飾器 → reset prop flag
        if stripped and not stripped.startswith("@") and not stripped.startswith("#"):
            prop_next = False

    # dedup（保留第一次出現）
    seen = set()
    uniq = []
    for n, k in results:
        if n in seen:
            continue
        seen.add(n)
        uniq.append((n, k))
    return uniq


def count_production_callers(name: str, kind: str, target: Path) -> tuple[int, list[str]]:
    """用 Python re 掃所有 .py 找呼叫點（Windows grep 不可靠，純 Python 實作）。
    - method 呼叫: `.name(`
    - property 讀取: `.name` 後接非識別字元
    排除 test 檔 + target 本檔。
    """
    if kind == "method":
        pattern = re.compile(rf"\.{re.escape(name)}\(")
    else:  # property
        pattern = re.compile(rf"\.{re.escape(name)}(?![A-Za-z0-9_])")

    target_norm = str(target).replace("\\", "/")
    real_callers: list[str] = []

    for py in PRODUCTION_ROOT.rglob("*.py"):
        fp = str(py).replace("\\", "/")
        if any(frag in fp for frag in EXCLUDE_FRAGMENTS):
            continue
        if target_norm in fp:
            continue
        if "__pycache__" in fp:
            continue
        try:
            content = py.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if pattern.search(content):
            real_callers.append(fp)

    return len(real_callers), real_callers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"掃描目標（預設 {DEFAULT_TARGET}）",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI 模式：有 dead config 即 exit 1",
    )
    args = parser.parse_args()

    items = find_public_methods_and_properties(args.target)
    print(f"=== Dead Config Scan: {args.target} ===")
    print(f"Public API surface: {len(items)} items\n")

    dead = []
    alive = []
    skipped = []
    for name, kind in items:
        if name in CONSTRUCTOR_PATTERNS:
            # Constructor 透過 factory 間接呼叫，scanner 無法追蹤；標 skipped 不算 dead
            skipped.append((name, kind, "constructor-via-factory"))
            continue
        n, callers = count_production_callers(name, kind, args.target)
        if n == 0:
            dead.append((name, kind))
        else:
            alive.append((name, kind, n))

    print(f"{'STATUS':8} {'KIND':10} {'NAME':35} {'CALLERS':>8}")
    print("-" * 65)
    for name, kind, n in alive:
        print(f"{'✓ ALIVE':8} {kind:10} {name:35} {n:>8}")
    for name, kind, reason in skipped:
        print(f"{'⊙ SKIP':8} {kind:10} {name:35} ({reason})")
    for name, kind in dead:
        print(f"{'✗ DEAD':8} {kind:10} {name:35} {'0':>8}")

    print(f"\nAlive: {len(alive)}  Dead: {len(dead)}  Skipped: {len(skipped)}")

    if dead:
        print("\n⚠️  Dead config 清單（定義但 0 生產呼叫）：")
        for name, kind in dead:
            print(f"   - {kind} {name}")
        print("\n修復路徑（擇一）：")
        print("  1. 接線：在生產呼叫點調用此 getter（參 e33df6fd SSOT 接線範本）")
        print("  2. 刪除：若確認無設計意圖，刪除 getter + yaml 欄位")
        print("  3. 註記：加 TODO docstring 說明 pending integration（參 5732465f）")

        if args.ci:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
