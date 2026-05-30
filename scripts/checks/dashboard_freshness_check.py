"""Fitness step 64 (v6.12, 2026-05-30): GOVERNANCE_INTEGRATED_DASHBOARD freshness 偵測

防 cron 06:00 regenerate silent fail → dashboard stale → owner session 啟動讀到舊資料。

YELLOW > 24h / RED > 48h
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


DASH = Path(__file__).resolve().parents[2] / "docs" / "architecture" / "GOVERNANCE_INTEGRATED_DASHBOARD.md"


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== GOVERNANCE_INTEGRATED_DASHBOARD freshness check (step 64) ===")
    if not DASH.exists():
        print(f"  🔴 RED — dashboard 不存在: {DASH}")
        return 1 if strict else 0

    mtime = datetime.fromtimestamp(DASH.stat().st_mtime)
    age_h = (datetime.now() - mtime).total_seconds() / 3600
    size = DASH.stat().st_size
    print(f"  path:   {DASH}")
    print(f"  mtime:  {mtime.isoformat()}")
    print(f"  age:    {age_h:.1f} hours")
    print(f"  size:   {size} bytes")
    print()

    if age_h > 48:
        print(f"  🔴 RED — dashboard > 48h 未更新（cron 06:00 silent fail?）")
        return 1 if strict else 0
    elif age_h > 24:
        print(f"  🟡 YELLOW — dashboard > 24h 但 ≤ 48h")
    else:
        print(f"  🟢 GREEN — dashboard 新鮮")
    return 0


if __name__ == "__main__":
    sys.exit(main())
