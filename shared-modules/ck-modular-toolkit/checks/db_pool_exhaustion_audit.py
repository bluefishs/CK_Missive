#!/usr/bin/env python3
"""db_pool_exhaustion_audit.py — fitness step 48

偵測 SQLAlchemy DB connection pool 耗盡風險（v6.12 P3 forward-looking）。

風險背景：
- SQLAlchemy pool exhausted 時新 connection 進入 wait queue（默認 30 秒 timeout）
- L29 family silent failure 模式：connection wait 不 alert，看似 OK 實際 latency 飆
- 業務 endpoint 慢但 docker healthcheck 仍 200 → silent dormant
- 觀察點：`/health` endpoint 已暴露 pool stats（{size, checked_in, checked_out, overflow, max_overflow}）

判定邏輯：
1. 抓 /health endpoint pool stats（local + public）
2. 計算 utilization = checked_out / (size + max_overflow)
3. RED：utilization > 90%（almost exhausted）
4. YELLOW：utilization > 50% 或 overflow > 0（已用到 overflow pool）
5. GREEN：utilization < 50% 且 overflow = 0

Usage:
    python scripts/checks/db_pool_exhaustion_audit.py [--strict]

Exit codes:
    0 = green (pool utilization healthy)
    1 = yellow (>50% util or overflow active)
    2 = red (>90% util, near exhaustion; --strict 時 yellow 也 exit 2)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

# Endpoints to audit (local + public)
HEALTH_ENDPOINTS = [
    ("local", "http://localhost:8001/health"),
    ("public", "https://missive.cksurvey.tw/health"),
]


def _curl_json(url: str, timeout: int = 5) -> dict | None:
    """Fetch URL and parse as JSON."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 2,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def _classify(pool: dict) -> tuple[str, float, str]:
    """Return (severity, utilization_pct, reason)."""
    size = pool.get("size", 0)
    checked_out = pool.get("checked_out", 0)
    overflow = pool.get("overflow", 0)
    max_overflow = pool.get("max_overflow", 0)

    capacity = size + max_overflow
    if capacity <= 0:
        return "GREEN", 0.0, "no capacity data"

    util_pct = (checked_out / capacity) * 100.0

    if util_pct > 90:
        return "RED", util_pct, f"utilization >{90}% — near exhaustion"
    if util_pct > 50 or overflow > 0:
        reason_parts = []
        if util_pct > 50:
            reason_parts.append(f"util {util_pct:.1f}%")
        if overflow > 0:
            reason_parts.append(f"overflow active ({overflow}/{max_overflow})")
        return "YELLOW", util_pct, " + ".join(reason_parts)
    return "GREEN", util_pct, f"util {util_pct:.1f}%"


def main() -> int:
    # Force UTF-8 stdout for Windows cp950 console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any warning")
    args = parser.parse_args()

    print("=" * 60)
    print("DB pool exhaustion audit (v6.12 P3)")
    print("v1.0 / detect connection pool exhaustion risk")
    print("=" * 60)

    overall_severity = "GREEN"
    any_reachable = False

    for name, url in HEALTH_ENDPOINTS:
        print(f"\n  {name}: {url}")
        data = _curl_json(url)
        if not data:
            print(f"    ⚪ unreachable (likely network issue)")
            continue

        any_reachable = True
        pool = data.get("pool") or {}
        if not pool:
            print(f"    ⚪ no pool stats in /health (older backend?)")
            continue

        severity, util_pct, reason = _classify(pool)
        indicator = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[severity]

        size = pool.get("size", 0)
        checked_out = pool.get("checked_out", 0)
        overflow = pool.get("overflow", 0)
        max_overflow = pool.get("max_overflow", 0)
        capacity = size + max_overflow

        print(f"    {indicator} {severity}: {reason}")
        print(f"       size={size} | checked_out={checked_out} | overflow={overflow}/{max_overflow}")
        print(f"       capacity={capacity} | utilization={util_pct:.1f}%")

        # Escalate overall
        if severity == "RED":
            overall_severity = "RED"
        elif severity == "YELLOW" and overall_severity == "GREEN":
            overall_severity = "YELLOW"

    if not any_reachable:
        print(f"\n  ⚪ no endpoint reachable — skipping audit")
        return 0

    print(f"\n  Final severity: {overall_severity}")

    if overall_severity == "RED":
        print("\n💡 修法建議：")
        print("  1. 立即 docker logs ck_missive_backend 看哪個 endpoint 長時間 hold connection")
        print("  2. 調 pool size: SQLALCHEMY_ENGINE_OPTIONS.pool_size + max_overflow")
        print("  3. 加 pool_pre_ping=True 防 stale connection")
        print("  4. 加 pool_recycle=3600（每小時刷新）")
        print("  5. review code 找未 close 的 session（特別 background scheduler）")
    elif overall_severity == "YELLOW":
        print("\n💡 informational：")
        print("  目前 overflow 已啟用或 utilization > 50% — 觀察是否常態化")
        print("  若 7 天內持續 yellow → 考慮提升 pool_size")

    if overall_severity == "RED":
        return 2
    if overall_severity == "YELLOW" and args.strict:
        return 2
    if overall_severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
