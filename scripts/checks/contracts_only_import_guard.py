#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 29 — Contracts Only Import Guard (v6.10 P1, 2026-05-18).

偵測「跨 bounded context 直 import 內部 module」反模式 — 強制走 contracts/。

依據：
- docs/architecture/CONTRACTS_LAYER_GUIDE.md
- docs/architecture/MODULARIZATION_STANDARDS_v1.md
- 整體架構律定方案規約 A（Bounded Context Contract Layer）

12 bounded contexts：document / contract / agency / vendor / audit / notification /
erp / integration / tender / calendar / wiki / system / backup

允許：
- 同 context 內部 import （e.g. document/ → document/）
- import contracts/（facade）
- import core/ (paths, config, db 等基礎)
- import base/ / repositories/

禁止：
- 跨 context 直 import 內部 module（e.g. document/ → calendar/X.py）

預期：v6.10 初次跑會有 50+ violations（已知 anti-pattern）。
目標：v7.0 前清到 0。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "backend" / "app" / "services"

# 12 bounded contexts（services/ 下的子目錄）
BOUNDED_CONTEXTS = {
    "document", "contract", "agency", "vendor", "audit", "notification",
    "erp", "integration", "tender", "calendar", "wiki", "system", "backup",
    "memory", "ai", "taoyuan",  # 衍生 context
}

# 允許跨 context import 的「中性」目錄
NEUTRAL_DIRS = {
    "contracts",  # facade layer 本身
    "base",       # 基礎 service
    "strategies", # 策略模式
}

# import pattern: from app.services.X.Y import ...
IMPORT_PATTERN = re.compile(r"from\s+app\.services\.(\w+)(?:\.(\w+))?")


def _scan_file(path: Path) -> list[dict]:
    rel = path.relative_to(SERVICES_DIR).as_posix()
    parts = rel.split("/")
    if len(parts) < 2:
        return []  # services/X.py 散戶不檢查
    my_context = parts[0]
    if my_context in NEUTRAL_DIRS:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    violations = []
    for m in IMPORT_PATTERN.finditer(text):
        other_context = m.group(1)
        if other_context == my_context:
            continue  # 同 context
        if other_context in NEUTRAL_DIRS:
            continue
        if other_context not in BOUNDED_CONTEXTS:
            continue  # 散戶 module（不算 cross-context）
        # 真跨 context import
        line_no = text[: m.start()].count("\n") + 1
        violations.append({
            "file": rel,
            "line": line_no,
            "my_context": my_context,
            "imported_context": other_context,
            "match": m.group(),
        })
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 29 — Contracts Only Import")
    parser.add_argument("--ci", action="store_true", help="strict mode")
    args = parser.parse_args()

    all_violations = []
    for p in sorted(SERVICES_DIR.rglob("*.py")):
        if "__pycache__" in p.parts or p.name == "__init__.py":
            continue
        all_violations.extend(_scan_file(p))

    print("=" * 60)
    print(f"Contracts Only Import Guard — scanned services/")
    print("=" * 60)
    print(f"\n  Total cross-context imports: {len(all_violations)}\n")

    # 統計：哪些 context 對 跨 import 最多
    pair_counts: dict[tuple[str, str], int] = {}
    for v in all_violations:
        key = (v["my_context"], v["imported_context"])
        pair_counts[key] = pair_counts.get(key, 0) + 1

    print("  Top cross-context dependency pairs:")
    for (src, dst), count in sorted(pair_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"    {src:<12} → {dst:<12} {count}")

    if len(all_violations) > 0:
        print("\n  Sample violations:")
        for v in all_violations[:10]:
            print(f"    L{v['line']:<5} {v['file']:<55} [{v['my_context']}→{v['imported_context']}] {v['match']}")

    if all_violations:
        print("\n修法建議：")
        print("  改走 contracts/facades/ (規劃中) 或使用 Port interface")
        print("  refer: docs/architecture/CONTRACTS_LAYER_GUIDE.md")

    return 1 if (args.ci and all_violations) else 0


if __name__ == "__main__":
    sys.exit(main())
