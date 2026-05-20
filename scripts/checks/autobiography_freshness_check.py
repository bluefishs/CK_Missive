#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 36 — Autobiography Scheduler Freshness Check (v6.10.2 B 配套)

防範 `memory_weekly_autobiography_job`（週日 18:00 cron）silent miss — 5/20 揭發
過去 5 個月該 cron 排程在但**未真實在週日 18:00 跑**（手動跑邏輯正常）。
本 check 偵測 wiki/memory/evolutions/2026-Wnn.md 最新檔對應週數，
若距當前週 > 1 週 → 警示 scheduler 可能 silent miss。

對應 OPTIMIZATION_PIPELINE.md 環節 4「Diary → Autobiography」健康度。

Exit codes:
  0 — autobiography 在 1 週內產出（健康）
  1 — --ci strict mode 且距離 > 2 週（必須 owner 介入排查）

Usage:
  python scripts/checks/autobiography_freshness_check.py
  python scripts/checks/autobiography_freshness_check.py --ci
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVOLUTIONS_DIR = PROJECT_ROOT / "wiki" / "memory" / "evolutions"

WEEK_FILENAME_RE = re.compile(r"^(\d{4})-W(\d{2})\.md$")


def get_latest_week_file() -> tuple[str | None, int | None, datetime | None]:
    """Returns (filename, week_number_yyyyww, file_mtime). None if no week files found."""
    if not EVOLUTIONS_DIR.exists():
        return (None, None, None)

    weeks = []
    for path in EVOLUTIONS_DIR.iterdir():
        m = WEEK_FILENAME_RE.match(path.name)
        if m:
            year, wk = int(m.group(1)), int(m.group(2))
            weeks.append((year * 100 + wk, path.name, path.stat().st_mtime))

    if not weeks:
        return (None, None, None)

    weeks.sort(reverse=True)
    yw, name, mtime = weeks[0]
    return (name, yw, datetime.fromtimestamp(mtime))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fitness step 36 — Autobiography Scheduler Freshness Check"
    )
    parser.add_argument(
        "--ci", action="store_true",
        help="strict mode: 距離當前週 > 2 週即 exit 1"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Autobiography Scheduler Freshness Check (B 配套)")
    print("v6.10.2 / wiki/memory/evolutions/ 週度產出健康度")
    print("=" * 60)
    print()

    if not EVOLUTIONS_DIR.exists():
        print(f"[ERROR] wiki/memory/evolutions/ 不存在: {EVOLUTIONS_DIR}", file=sys.stderr)
        return 1 if args.ci else 0

    name, latest_yw, mtime = get_latest_week_file()
    if not name:
        print("[FAIL] 0 個 autobiography 檔案 — 環節 4 嚴重 dormant")
        print()
        print("Fix guidance:")
        print("  1. 手動跑：python -c \"import asyncio; ...; AutobiographyGenerator(db).run()\"")
        print("  2. 檢查 scheduler.py memory_weekly_autobiography_job 排程")
        print("  3. 看 backend log 過去 4 週日 18:00 是否有 'Memory Weekly Autobiography' 訊息")
        return 1 if args.ci else 0

    # 當前週號（ISO week）
    now = datetime.now()
    iso_year, iso_week, _ = now.isocalendar()
    current_yw = iso_year * 100 + iso_week
    weeks_gap = (current_yw - latest_yw) if latest_yw is not None else 0

    print(f"  最新 autobiography: {name}")
    print(f"  檔案 mtime: {mtime.strftime('%Y-%m-%d %H:%M:%S') if mtime else 'unknown'}")
    print(f"  當前週: {iso_year}-W{iso_week:02d}")
    print(f"  落後週數: {weeks_gap}")
    print()

    if weeks_gap <= 0:
        print("[PASS] autobiography 在當前週或更新")
        return 0
    elif weeks_gap == 1:
        print("[INFO] 落後 1 週（週日尚未到 / 上週剛跑完）")
        return 0
    elif weeks_gap == 2:
        print("[WARN] 落後 2 週 — 可能 scheduler 1 次 silent miss")
        print("  建議：tail -50 logs/backend.log | grep 'autobiography'")
        return 0
    else:
        print(f"[FAIL] 落後 {weeks_gap} 週 — scheduler 持續 silent miss")
        print()
        print("Fix guidance:")
        print("  1. 確認 PM2 / backend container 在週日 18:00 真實 alive")
        print("  2. 檢查 APScheduler misfire_grace_time（預設 1s 過時即 skip）")
        print("  3. 手動補跑：上個週的 autobiography")
        print("  4. 5/20 揭發過去 5 個月 silent miss — root cause 可能仍未根治")
        return 1 if args.ci else 0


if __name__ == "__main__":
    sys.exit(main())
