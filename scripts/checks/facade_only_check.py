#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 32 - Facade Only Check (v6.10 P1 Phase B, 2026-05-18).

step 29 的進階版：偵測「跨 bounded context 直 import 內部 module」
但允許 facades/ 與 contracts/ 的 import 為合規。

step 32 的價值（vs step 29）：
- step 29 baseline 84 cross-context imports
- step 32 開始要求新 PR 不得增加 cross-context（v6.11 strict 模式）
- 同時提供「應走哪個 facade」的指引

依據:
- docs/architecture/CONTRACTS_LAYER_GUIDE.md
- docs/architecture/NAMING_CONVENTIONS.md
- v6.10 Phase B 12 facades 落地

Exit codes:
  0 - 無新增違規（與 baseline 持平）
  1 - strict + 新增違規 > 0
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "backend" / "app" / "services"

# 12 bounded contexts + 其他 services 散戶
BOUNDED_CONTEXTS = {
    "document", "contract", "agency", "vendor", "audit", "notification",
    "erp", "integration", "tender", "calendar", "wiki", "system", "backup",
    "memory", "ai", "taoyuan",
}

# Facade 對應建議（給 violation 修法指引）
CONTEXT_TO_FACADE = {
    "document": "DocumentFacade",
    "contract": "ContractFacade",
    "agency": "AgencyFacade",
    "vendor": "VendorFacade",
    "audit": "AuditFacade",
    "notification": "NotificationFacade",
    "erp": "ERPFacade",
    "integration": "IntegrationFacade",
    "calendar": "CalendarFacade",
    "wiki": "WikiFacade",
    "memory": "MemoryFacade",
    "ai": "AIFacade",
}

NEUTRAL_DIRS = {"contracts", "base", "strategies"}

IMPORT_PATTERN = re.compile(r"from\s+app\.services\.(\w+)(?:\.(\w+))?")


def _scan_file(path: Path) -> list[dict]:
    rel = path.relative_to(SERVICES_DIR).as_posix()
    parts = rel.split("/")
    if len(parts) < 2:
        return []
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
            continue
        if other_context in NEUTRAL_DIRS:
            continue
        if other_context not in BOUNDED_CONTEXTS:
            continue
        line_no = text[: m.start()].count("\n") + 1
        suggestion = CONTEXT_TO_FACADE.get(other_context, "facade (TBD)")
        violations.append({
            "file": rel,
            "line": line_no,
            "my_context": my_context,
            "imported_context": other_context,
            "match": m.group(),
            "suggestion": f"use {suggestion} via app.services.contracts.facades",
        })
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 32 - Facade Only Check")
    parser.add_argument("--ci", action="store_true", help="strict mode")
    parser.add_argument("--baseline", type=int, default=84,
                        help="baseline cross-context count (default: 84 from step 29)")
    args = parser.parse_args()

    all_violations = []
    for p in sorted(SERVICES_DIR.rglob("*.py")):
        if "__pycache__" in p.parts or p.name == "__init__.py":
            continue
        all_violations.extend(_scan_file(p))

    count = len(all_violations)
    print("=" * 60)
    print(f"Facade Only Check (step 32) - v6.10 P1")
    print("=" * 60)
    print(f"\n  Current cross-context imports: {count}")
    print(f"  Baseline (step 29):             {args.baseline}")
    print(f"  Delta:                          {count - args.baseline:+d}")

    if count > args.baseline:
        print(f"\n  [WARN] New cross-context imports added beyond baseline!")
    elif count < args.baseline:
        print(f"\n  [OK] {args.baseline - count} cross-context imports cleared since baseline")

    # Top context pairs
    pair_counts: dict[tuple, int] = defaultdict(int)
    for v in all_violations:
        pair_counts[(v["my_context"], v["imported_context"])] += 1

    print("\n  Top remaining cross-context dependency pairs:")
    for (src, dst), cnt in sorted(pair_counts.items(), key=lambda x: -x[1])[:10]:
        facade = CONTEXT_TO_FACADE.get(dst, "facade-TBD")
        print(f"    {src:<12} -> {dst:<12} {cnt:<3} (use {facade})")

    if all_violations:
        print("\n  Sample violations:")
        for v in all_violations[:8]:
            print(f"    L{v['line']:<5} {v['file']:<55} [{v['my_context']}->{v['imported_context']}]")
            print(f"            -> {v['suggestion']}")

    if args.ci and count > args.baseline:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
