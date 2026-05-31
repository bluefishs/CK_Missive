#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: services/ 頂層散戶比例

STANDARD_REFERENCE.md §12 要求：services/ 頂層散戶比例 < 20%

目標：阻止 services/ 頂層持續膨脹，強制新 service 入 bounded context 子包。

用法：
    python scripts/checks/service_dir_entropy.py
    python scripts/checks/service_dir_entropy.py --ci    # CI 模式：超閾值 exit 1
    python scripts/checks/service_dir_entropy.py --threshold 0.20

關聯：
    - docs/architecture/STANDARD_REFERENCE.md §1 服務層 DDD 組織
    - docs/architecture/SERVICE_CONTEXT_MAP.md (85 散戶 → 16 context 映射)
    - memory/feedback_ddd_over_line_count.md

Version: 1.0.0 (2026-04-25)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# v6.13 (2026-05-31) L52 family 第 10 案: container fallback
SERVICES_ROOT = Path("backend/app/services")
if not SERVICES_ROOT.exists() and Path("app/services").exists():
    SERVICES_ROOT = Path("app/services")


def count_services() -> tuple[int, int, list[str]]:
    """回傳 (total, in_subpackages, top_level_files)"""
    if not SERVICES_ROOT.exists():
        print(f"ERROR: {SERVICES_ROOT} not found", file=sys.stderr)
        sys.exit(2)

    top_level = []
    in_subpackages = 0

    for item in SERVICES_ROOT.iterdir():
        if item.name in {"__init__.py", "__pycache__"}:
            continue
        if item.is_file() and item.suffix == ".py":
            top_level.append(item.name)
        elif item.is_dir() and not item.name.startswith("__"):
            for sub in item.rglob("*.py"):
                if sub.name != "__init__.py":
                    in_subpackages += 1

    total = len(top_level) + in_subpackages
    return total, in_subpackages, sorted(top_level)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.20,
        help="最大散戶比例（預設 0.20 = 20%%）",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI 模式：超閾值 exit 1（本地僅警告 exit 0）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="列出所有頂層散戶檔名",
    )
    args = parser.parse_args()

    total, in_sub, top_level = count_services()
    entropy = len(top_level) / total if total else 0.0

    status = "✓" if entropy < args.threshold else "✗"
    print(f"{status} services/ directory entropy")
    print(f"  Total services:    {total}")
    print(f"  In subpackages:    {in_sub}")
    print(f"  Top-level orphans: {len(top_level)}")
    print(f"  Entropy:           {entropy:.1%} (threshold: {args.threshold:.0%})")

    if args.verbose or entropy >= args.threshold:
        print(f"\nTop-level files ({len(top_level)}):")
        for f in top_level:
            print(f"  - {f}")
        print(f"\n📘 參考 docs/architecture/SERVICE_CONTEXT_MAP.md 將上述檔案遷移至對應 bounded context 子包")

    if entropy >= args.threshold:
        msg = f"\n⚠️  散戶比例 {entropy:.1%} ≥ 閾值 {args.threshold:.0%}"
        if args.ci:
            print(msg + " — CI FAIL", file=sys.stderr)
            return 1
        print(msg + " — local warning (use --ci for hard fail)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
