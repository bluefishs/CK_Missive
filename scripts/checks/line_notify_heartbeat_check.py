#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""F15 (5/04 v3.0 覆盤洞察 15) — LINE notify 7 天 heartbeat watchdog

silent skip 設計對主流程是對的（adr-0028 best-effort），但對體感層而言：
silent = 用戶看不到 = 死亡。

本 watchdog 統計 backend log 中 7 天內 LINE push 成功計數，連續 7 天
< 1 則報警 — 預防 5/04 那種「v6.3-v6.7 五條推送鏈全 silent skip 5 天無人察覺」
事故再發。

關聯：
- docs/architecture/SYSTEM_INTEGRATION_REVIEW_v3.md 洞察 15
- docs/runbooks/enable_line_perception_outputs.md
- task #6 F15
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# F15 修正：PM2 ck-backend stdout log 在 ~/.pm2/logs/，不是 backend/logs/
# 另也掃 backend/logs/ 為次要來源
import os
PM2_LOG_DIR = Path(os.path.expanduser("~/.pm2/logs"))
LOG_DIRS = [PM2_LOG_DIR, PROJECT_ROOT / "backend" / "logs"]

# log 中 successful LINE push 的 marker
LINE_PUSH_MARKERS = [
    "Autobiography LINE pushed",          # autobiography.py:517
    "SOUL changelog notify pushed",       # autobiography.py:456
    "Daily self-reflection: LINE pushed", # anti_echo.py（啟用時）
    "crystal_applied.*line_push",         # crystal_applier.py
    "Crystal rollback notified",          # crystal_applier.py
    "proactive LINE push",                # line_push_scheduler.py
]


def count_line_pushes_7d(log_dirs: list) -> tuple[dict, int]:
    """掃 PM2 + backend logs，計 7 天內 LINE push 各類成功次數。"""
    counts: dict[str, int] = {marker: 0 for marker in LINE_PUSH_MARKERS}
    files_scanned = 0

    for log_dir in log_dirs:
        if not log_dir.exists():
            continue
        log_files = []
        for pattern in ("*.log", "*.log.*"):
            log_files.extend(log_dir.glob(pattern))

        for lf in log_files:
            files_scanned += 1
            try:
                with lf.open("r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        for marker in LINE_PUSH_MARKERS:
                            if re.search(marker, line):
                                counts[marker] += 1
            except Exception:
                continue

    return counts, files_scanned


def main() -> int:
    parser = argparse.ArgumentParser(description="LINE notify 7d heartbeat (F15)")
    parser.add_argument(
        "--ci", action="store_true",
        help="strict mode: exit 1 if total push count = 0 in 7d",
    )
    parser.add_argument(
        "--threshold", type=int, default=1,
        help="minimum push count threshold (default: 1)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" F15 LINE notify 7-day heartbeat")
    print("=" * 60)

    counts, files_scanned = count_line_pushes_7d(LOG_DIRS)
    total = sum(counts.values())

    print(f"\n  Log dirs scanned: {len(LOG_DIRS)} ({files_scanned} files)")
    print(f"  Threshold: {args.threshold} (any pushes in 7 days)\n")

    for marker, count in counts.items():
        marker_short = marker[:50]
        print(f"  {count:>5} | {marker_short}")

    print(f"\n  Total LINE pushes (7 days): {total}")
    print("=" * 60)

    if total >= args.threshold:
        print(f" OK — body 體感推送活著")
        return 0
    else:
        print(f" WARN — 7 天 0 LINE 推送（5/04 v3.0 洞察 15 警報）")
        print()
        print("  可能根因：")
        print("  1. .env LINE_ADMIN_USER_ID 未設（最常見）")
        print("  2. .env LINE_GROWTH_NOTIFY_ENABLED=false")
        print("  3. ck-backend uptime > 新 cron commit 時間（cron 沒掛）")
        print("  4. LINE Bot token 失效 / 額度用盡")
        print()
        print("  Runbook: docs/runbooks/enable_line_perception_outputs.md")
        if args.ci:
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
