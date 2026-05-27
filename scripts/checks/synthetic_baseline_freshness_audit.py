#!/usr/bin/env python3
"""synthetic_baseline_freshness_audit.py — fitness step 49

偵測 synthetic_baseline_inject scheduler job 是否陷入 silent dead loop
（v6.12 P3 forward-looking — 補 5/22~5/27 6+ 天 silent dead 之防禦）。

風險背景：
- `agent_post_processing` cron job 每日 09:00 / 14:00 注入合成 baseline query
- 失敗時 scheduler 只 logger.warning（per L29 family）→ 不觸發 alert
- 5/22 起 docker container `MCP_SERVICE_TOKEN` env missing →
  endpoint 403 in 8-11ms → cron rc=1 每跑都 Error=10/10
- 6+ 天無人察覺，直到 owner 跑 v7 baseline 才揭發
- L48 同型：silent dormant + missing audit enforcement

判定邏輯：
1. 掃 `backend/logs/backend-error.log` 最近 24h 內含 `synthetic_baseline_inject` 的行
2. 區分 success vs failed
3. 若最近 24h 內：
   - 0 行 → YELLOW（scheduler 未跑或日誌輪替；視為觀察）
   - 全失敗（Error≥Total）→ RED（chronic silent dead，同 5/22-5/27 模式）
   - 部分失敗（>30% fail rate）→ YELLOW
   - 全成功 → GREEN
4. 若無 log 檔 → YELLOW（無法判定，可能 dev env）

Usage:
    python scripts/checks/synthetic_baseline_freshness_audit.py [--strict] [--hours N]

Exit codes:
    0 = green (all recent runs succeeded)
    1 = yellow (partial failures or no data)
    2 = red (all runs failed for >24h)
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = PROJECT_ROOT / "backend" / "logs" / "backend-error.log"

# Match scheduler log line for synthetic_baseline_inject
# Example: "synthetic_baseline_inject failed (rc=1): Total=10 Success=0 Error=10 Timeout=0"
# Or:      "synthetic_baseline_inject: ok"
_RE_RESULT = re.compile(
    r"synthetic_baseline_inject"
    r"(?:\s+failed\s*\(rc=\d+\))?"
    r"[:\s].*?"
    r"Total=(?P<total>\d+)\s+Success=(?P<success>\d+)\s+Error=(?P<error>\d+)",
    re.IGNORECASE | re.DOTALL,
)

# Loose timestamp match for log line prefix: YYYY-MM-DD HH:MM:SS
_RE_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}T?\s?\d{2}:\d{2}:\d{2})")


def _parse_ts(line: str) -> datetime | None:
    """Extract leading timestamp from log line."""
    m = _RE_TS.match(line)
    if not m:
        return None
    ts_raw = m.group(1).replace("T", " ").strip()
    try:
        return datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _scan_log(hours: int) -> tuple[list[dict], bool]:
    """Scan log file for synthetic_baseline events in last N hours."""
    if not LOG_PATH.exists():
        return [], False

    cutoff = datetime.now() - timedelta(hours=hours)
    events: list[dict] = []

    # Read last ~2000 lines to avoid loading huge log files
    try:
        with LOG_PATH.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-5000:]
    except Exception:
        return [], False

    for line in lines:
        if "synthetic_baseline_inject" not in line:
            continue
        ts = _parse_ts(line)
        if ts and ts < cutoff:
            continue
        m = _RE_RESULT.search(line)
        if not m:
            continue
        total = int(m.group("total"))
        success = int(m.group("success"))
        error = int(m.group("error"))
        events.append({
            "ts": ts.isoformat() if ts else "?",
            "total": total, "success": success, "error": error,
            "rc_failed": "failed (rc=" in line,
        })
    return events, True


def _classify(events: list[dict], has_log: bool) -> tuple[str, str]:
    """Return (severity, reason)."""
    if not has_log:
        return "YELLOW", "no log file (dev env or rotated)"
    if not events:
        return "YELLOW", "no synthetic_baseline runs in window (scheduler off or rotated)"

    total_runs = len(events)
    total_success = sum(e["success"] for e in events)
    total_error = sum(e["error"] for e in events)
    total_attempts = total_success + total_error
    if total_attempts == 0:
        return "YELLOW", "events exist but Total=0 across runs"

    error_rate = total_error / total_attempts
    if total_success == 0 and total_error > 0:
        return "RED", f"all {total_attempts} attempts failed across {total_runs} runs (chronic silent dead)"
    if error_rate > 0.30:
        return "YELLOW", f"high error rate {error_rate:.0%} over {total_runs} runs"
    return "GREEN", f"{total_success}/{total_attempts} succeeded over {total_runs} runs"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any warning")
    parser.add_argument("--hours", type=int, default=24, help="window in hours (default 24)")
    args = parser.parse_args()

    print("=" * 60)
    print("Synthetic baseline freshness audit (v6.12 P3 — L48 防禦)")
    print(f"v1.0 / detect chronic silent failure (window {args.hours}h)")
    print("=" * 60)

    events, has_log = _scan_log(args.hours)
    severity, reason = _classify(events, has_log)
    indicator = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[severity]

    print(f"\n  log path: {LOG_PATH}")
    print(f"  events in {args.hours}h: {len(events)}")

    if events:
        total_success = sum(e["success"] for e in events)
        total_error = sum(e["error"] for e in events)
        print(f"  cumulative success: {total_success}")
        print(f"  cumulative error:   {total_error}")
        # Show first + last for context
        print(f"  first event:        {events[0]['ts']}  Total={events[0]['total']} Success={events[0]['success']} Error={events[0]['error']}")
        print(f"  last event:         {events[-1]['ts']}  Total={events[-1]['total']} Success={events[-1]['success']} Error={events[-1]['error']}")

    print(f"\n  {indicator} {severity}: {reason}")

    if severity == "RED":
        print("\n💡 修法建議（chronic silent dead，常見原因）：")
        print("  1. 確認 docker container 是否有 MCP_SERVICE_TOKEN env")
        print("     `docker exec ck_missive_backend env | grep MCP_SERVICE_TOKEN`")
        print("  2. 若 endpoint 改 path / auth → 同步 scripts/checks/synthetic-baseline-inject.py")
        print("  3. 手動跑驗證：`python scripts/checks/synthetic-baseline-inject.py --count 1`")
        print("  4. 看 backend log 抓 403 / 401 / 5xx 真因")
        print("  5. 補 Prometheus alert（synthetic_baseline_error_rate > 0.5 持續 24h）")
    elif severity == "YELLOW":
        print("\n💡 informational：")
        print("  - 若 7 天內持續 yellow → 觀察是否 scheduler 已停跑")
        print("  - log 輪替頻繁可加大 --hours window")

    if severity == "RED":
        return 2
    if severity == "YELLOW" and args.strict:
        return 2
    if severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
