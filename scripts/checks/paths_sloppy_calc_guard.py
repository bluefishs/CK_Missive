#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 30 — Paths Sloppy Calc Guard (v6.10 P1-E, 2026-05-18).

防止散戶用 Path(__file__).parent.parent.parent... 或 Path(__file__).resolve().parents[N]
自算 project_root，必須走 app.core.paths SSOT。

起因：5/18 揭發 backup_scheduler path bug（Wave 8 遷子包後 parents[N] 未同步），
靜默寫到 backend/backups/ 而非專案根 backups/，dormant 兩個月才被發現。

律定（規約 E）：禁止新代碼用 `Path(__file__).parents[` 或 `parent.parent.parent`，
必須 from app.core.paths import ...

Exit codes:
  0 — 無違規 / strict 未觸發
  1 — strict mode (--ci) 且發現未豁免的散戶計算

Usage:
  python scripts/checks/paths_sloppy_calc_guard.py
  python scripts/checks/paths_sloppy_calc_guard.py --ci
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend" / "app"

# 兩種反模式 pattern
PATTERN_PARENTS_BRACKET = re.compile(r"Path\(__file__\)\.resolve\(\)\.parents\[\d+\]")
PATTERN_PARENT_CHAIN = re.compile(r"Path\(__file__\)(?:\.resolve\(\))?\.parent(?:\.parent){2,}")

# 豁免名單（已對接 SSOT 的檔，或合理例外）
EXEMPT_FILES = {
    "core/paths.py",  # SSOT 自身
    "scripts/checks/paths_sloppy_calc_guard.py",  # 本守護腳本
}


def _scan_file(path: Path) -> list[dict]:
    rel = path.relative_to(BACKEND_DIR).as_posix()
    if rel in EXEMPT_FILES or any(rel.endswith(x) for x in EXEMPT_FILES):
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    violations = []
    for label, pattern in (("parents[N]", PATTERN_PARENTS_BRACKET),
                            ("parent.parent.parent", PATTERN_PARENT_CHAIN)):
        for m in pattern.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            violations.append({"file": rel, "line": line_no,
                               "pattern": label, "match": m.group()})
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 30 — paths SSOT guard")
    parser.add_argument("--ci", action="store_true", help="strict mode")
    args = parser.parse_args()

    all_violations = []
    for p in sorted(BACKEND_DIR.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        all_violations.extend(_scan_file(p))

    print("=" * 60)
    print(f"Paths Sloppy Calc Guard — scanned backend/app/")
    print("=" * 60)
    print(f"\n  Total violations: {len(all_violations)}\n")

    for v in all_violations[:30]:
        print(f"  L{v['line']:<5} {v['file']:<55} [{v['pattern']}] {v['match']}")

    if len(all_violations) > 30:
        print(f"\n  ... and {len(all_violations) - 30} more")

    if all_violations:
        print("\n修法建議：")
        print("  from app.core.paths import PROJECT_ROOT, BACKUP_DB_DIR, WIKI_DIR, ...")
        print("  取代散戶 Path(__file__).resolve().parents[N] 計算")

    return 1 if (args.ci and all_violations) else 0


if __name__ == "__main__":
    sys.exit(main())
