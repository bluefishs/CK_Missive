"""Diary density audit (L51.7 Sprint 2.P2.11 / fitness step 59, 2026-05-30)

監測 wiki/memory/diary/ 內容密度 (含 entity tag 的 entries 比例)，
推升 v7_reference_density_diary_pct 從 16.7% → ≥30%。

設計：
- 掃近 30d diary 內 ## 時間戳 entries
- 計算含 `**entities**:` 或 `[[wiki-link]]` 或 `kg_entity_id:` 的比例
- < 20% → RED / 20-30% → YELLOW / ≥ 30% → GREEN

Usage:
  python scripts/checks/diary_density_audit.py
  python scripts/checks/diary_density_audit.py --strict
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


WIKI_MEMORY = Path("wiki/memory")
ENTITY_PATTERNS = [
    r"\*\*entities\*\*\s*[:：]",
    r"\[\[[^\]]+\]\]",
    r"kg_entity_id\s*[:：]",
    r"#entity/",
]


def main(strict: bool = False, days: int = 30) -> int:
    print(f"=== Diary Density Audit (L51.7 Sprint 2.P2.11 / fitness 59) ===")
    print(f"  window: last {days} days")
    diary_dir = WIKI_MEMORY / "diary"
    if not diary_dir.exists():
        print(f"  [SKIP] {diary_dir} not found")
        return 0

    cutoff = date.today() - timedelta(days=days)
    total_entries = 0
    entries_with_entity = 0
    files_scanned = 0

    pattern_or = re.compile("|".join(ENTITY_PATTERNS))

    for f in diary_dir.glob("20*.md"):
        try:
            day = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if day < cutoff:
            continue
        files_scanned += 1
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # 按 ## 時間戳分 entry
        entries = re.split(r"^## \d{2}:\d{2}:\d{2}", text, flags=re.MULTILINE)[1:]
        for entry in entries:
            total_entries += 1
            if pattern_or.search(entry):
                entries_with_entity += 1

    if total_entries == 0:
        print(f"  [SKIP] no entries in last {days}d")
        return 0

    pct = entries_with_entity / total_entries * 100
    print(f"  files: {files_scanned}")
    print(f"  entries total: {total_entries}")
    print(f"  entries with entity tag: {entries_with_entity}")
    print(f"  density: {pct:.1f}%")
    print()

    if pct < 20:
        level = "RED"
        reason = "density < 20% — 大量 entry 缺 entity 引用"
    elif pct < 30:
        level = "YELLOW"
        reason = "density 20-30% — 目標 ≥30%"
    else:
        level = "GREEN"
        reason = f"density ≥ 30% (v7 target met)"
    print(f"Status: [{level}] {reason}")
    print()
    print("提升建議:")
    print(f"  • diary entry 加 **entities**: [實體列表]")
    print(f"  • 或 [[wiki-link]] 引用相關頁面")
    print(f"  • 或寫 kg_entity_id: <UUID>")

    if strict and level == "RED":
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    sys.exit(main(strict=args.strict, days=args.days))
