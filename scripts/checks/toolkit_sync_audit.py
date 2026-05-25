#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 33 - Toolkit Sync Audit (v6.10 P1, 2026-05-18).

偵測 ck-modular-toolkit 與 master scripts/ 是否分歧。

策略：scripts/checks/ 為 master，shared-modules/ck-modular-toolkit/ 為 auto-synced copy.
分歧時 fitness 跑 warning，--ci 模式 fail.

依據:
- 選項 D 統一同步策略
- 防 toolkit 落後 master 反模式

Exit codes:
  0 - 全同步
  1 - --ci + 有分歧
"""
from __future__ import annotations

import argparse
import filecmp
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# master path -> toolkit relative path
SYNC_MAP = {
    "scripts/checks/module_portability_audit.py":
        "shared-modules/ck-modular-toolkit/checks/module_portability_audit.py",
    "scripts/checks/naming_convention_audit.py":
        "shared-modules/ck-modular-toolkit/checks/naming_convention_audit.py",
    "scripts/checks/data/business_keyword_blacklist.yml":
        "shared-modules/ck-modular-toolkit/checks/data/business_keyword_blacklist.yml",
    "docs/architecture/NAMING_CONVENTIONS.md":
        "shared-modules/ck-modular-toolkit/standards/NAMING_CONVENTIONS.md",
    "docs/architecture/CONTRACTS_LAYER_GUIDE.md":
        "shared-modules/ck-modular-toolkit/standards/CONTRACTS_LAYER_GUIDE.md",
    "docs/architecture/CONTRACTS_MIGRATION_PATTERN.md":
        "shared-modules/ck-modular-toolkit/standards/CONTRACTS_MIGRATION_PATTERN.md",
    "docs/architecture/MODULAR_INVENTORY.md":
        "shared-modules/ck-modular-toolkit/standards/MODULAR_INVENTORY.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 33 - Toolkit Sync Audit")
    parser.add_argument("--ci", action="store_true", help="strict mode")
    args = parser.parse_args()

    diff_count = 0
    missing_count = 0
    ok_count = 0
    diff_files = []

    for master_rel, toolkit_rel in SYNC_MAP.items():
        master = PROJECT_ROOT / master_rel
        toolkit = PROJECT_ROOT / toolkit_rel
        if not master.exists():
            continue
        if not toolkit.exists():
            missing_count += 1
            diff_files.append((master_rel, "MISSING"))
            continue
        if not filecmp.cmp(master, toolkit, shallow=False):
            diff_count += 1
            diff_files.append((master_rel, "DIFF"))
        else:
            ok_count += 1

    print("=" * 60)
    print("Toolkit Sync Audit (step 33) - v6.10 P1")
    print("=" * 60)
    print(f"\n  Files in sync map: {len(SYNC_MAP)}")
    print(f"    [OK]      {ok_count}")
    print(f"    [DIFF]    {diff_count}")
    print(f"    [MISSING] {missing_count}")

    if diff_files:
        print("\n  Out-of-sync files:")
        for f, status in diff_files:
            print(f"    [{status}] {f}")
        print("\n  Run: bash scripts/sync_toolkit.sh")

    total_bad = diff_count + missing_count
    if args.ci and total_bad > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
