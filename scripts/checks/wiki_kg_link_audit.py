#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: Wiki ↔ KG 雙向引用率審計

CONSCIOUSNESS_INTEGRATION_ANALYSIS.md §4.2 整合斷鏈：
- Wiki: 243 pages 聲稱有 frontmatter `kg_entity_id` 連結 KG
- 實測：僅 30% 連結（75/243），dispatch 類別 0% 連結
- 影響：Wiki ↔ KG 搜尋互通性受限，Memory Wiki 與 KG 形同雙獨立來源

本 detector 按 entity_type 分組統計連結率，找出最大缺口；
Backfill 需另寫腳本（涉及 KG entity 名稱匹配，本檔僅 audit）。

用法：
    python scripts/checks/wiki_kg_link_audit.py
    python scripts/checks/wiki_kg_link_audit.py --threshold 80   # 連結率閾值
    python scripts/checks/wiki_kg_link_audit.py --ci              # 低於閾值 exit 1

Version: 1.0.0 (2026-04-25)
關聯:
- docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md §4.2
- backend/app/services/wiki_compiler.py（未來 backfill 切入點）
- ADR-0022 Memory Wiki self-evolving assistant
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict


WIKI_ROOT = Path("wiki")
SCAN_SUBDIRS = ["entities", "topics", "synthesis", "sources"]


def audit() -> dict:
    """掃 wiki frontmatter 統計 kg_entity_id 連結率"""
    by_type: dict[str, dict] = defaultdict(lambda: {"total": 0, "linked": 0, "unlinked_examples": []})
    grand_total = 0
    grand_linked = 0

    for sub in SCAN_SUBDIRS:
        d = WIKI_ROOT / sub
        if not d.is_dir():
            continue
        for md in d.iterdir():
            if not md.is_file() or md.suffix != ".md":
                continue
            try:
                src = md.read_text(encoding="utf-8")[:2000]
            except Exception:
                continue
            grand_total += 1
            kg_match = re.search(r"^kg_entity_id:\s*(\S+)", src, re.M)
            et_match = re.search(r"^entity_type:\s*(\S+)", src, re.M)
            entity_type = et_match.group(1) if et_match else "unknown"
            by_type[entity_type]["total"] += 1
            if kg_match and kg_match.group(1) not in ("null", "None", "", "~"):
                grand_linked += 1
                by_type[entity_type]["linked"] += 1
            else:
                if len(by_type[entity_type]["unlinked_examples"]) < 3:
                    by_type[entity_type]["unlinked_examples"].append(f"{sub}/{md.name}")

    return {
        "grand_total": grand_total,
        "grand_linked": grand_linked,
        "by_type": dict(by_type),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--threshold", type=int, default=80, help="連結率閾值（預設 80%%）")
    parser.add_argument("--ci", action="store_true", help="低於閾值 exit 1")
    args = parser.parse_args()

    print("=== Wiki ↔ KG Link Audit ===\n")

    result = audit()
    total = result["grand_total"]
    linked = result["grand_linked"]
    rate = linked * 100 // max(total, 1)

    status = "✓" if rate >= args.threshold else "✗"
    print(f"{status} 整體連結率: {linked}/{total} ({rate}%)")
    print(f"   閾值: {args.threshold}%（CONSCIOUSNESS §4.2 目標）")
    print()

    print(f"{'entity_type':25} {'linked':>10} {'total':>10} {'rate':>8}")
    print("-" * 60)
    for et in sorted(result["by_type"], key=lambda x: -result["by_type"][x]["total"]):
        c = result["by_type"][et]
        et_rate = c["linked"] * 100 // max(c["total"], 1)
        flag = ""
        if c["total"] >= 50 and et_rate < 20:
            flag = " 🔴 critical gap"
        elif c["total"] >= 10 and et_rate < 50:
            flag = " 🟡 needs backfill"
        print(f"{et:25} {c['linked']:>10} {c['total']:>10} {et_rate:>7}%{flag}")

    # Critical gap 詳情
    critical = [
        et for et, c in result["by_type"].items()
        if c["total"] >= 50 and c["linked"] * 100 // max(c["total"], 1) < 20
    ]
    if critical:
        print(f"\n🔴 Critical gap 類別（>=50 但 <20% 連結）：")
        for et in critical:
            c = result["by_type"][et]
            print(f"\n  entity_type={et} ({c['linked']}/{c['total']})")
            for ex in c["unlinked_examples"]:
                print(f"    例: {ex}")

    if rate < args.threshold:
        print(f"\n⚠️  整體連結率 {rate}% < 閾值 {args.threshold}%")
        print("修復路徑（建議）：")
        print("  1. 短期：寫 backfill 腳本按 wiki title 模糊匹配 KG canonical_entity")
        print("  2. 長期：wiki_compiler.py 在 compile phase 主動查 KG 補 frontmatter")
        print("  3. 已連結 30% 集中於 org/project — 可作為匹配模式參考")
        if args.ci:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
