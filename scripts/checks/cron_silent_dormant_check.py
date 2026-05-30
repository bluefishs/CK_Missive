"""Fitness step (v6.12 #2 補完): cron silent dormant 偵測

從 /metrics 讀 scheduler_job_last_run_age_seconds，找 age 超過 normal_interval × 2 的 cron。

設計：
- 不知道 normal interval 的 job → SKIP (前提：每個 job 設 max_age_threshold)
- 已知 interval (cron expression 推算) → 超 threshold = RED
- 配合 fitness daily / weekly 雙頻 forcing

注：每個 cron 該有自己的 SLO interval。本檢查使用保守 threshold 對映表。
"""
from __future__ import annotations

import sys
import urllib.request


# 每個 cron 的 max age 容忍 (sec) — interval × 2 估
# (interval 推自 scheduler.py 的 add_job trigger)
JOB_MAX_AGE = {
    # interval-based
    "process_reminders": 600,        # 5min × 2
    "cleanup_events": 86400 * 2,     # 1d × 2
    # cron-based
    "einvoice_sync": 7200,           # 1h × 2
    "erp_graph_ingest": 7200,
    "code_graph_incremental": 1800,  # 15min × 2
    "db_graph_refresh": 1800,
    "kb_coverage_check": 7200,
    "security_scan": 86400 * 2,
    "proactive_trigger_scan": 7200,
    "tender_dashboard_warm": 1800,
    "shadow_baseline": 86400,
    "wiki_compile": 86400 * 8,       # 週一 → 8d
    "wiki_lint": 86400 * 8,
    "fitness_daily": 86400 * 2,
    "fitness_weekly": 86400 * 8,
    "daily_self_retrospective": 86400 * 2,
    "crystal_review_overdue_alarm": 86400 * 2,
    "line_weekly_pulse": 86400 * 8,
    "kunge_weekly_learning_summary": 86400 * 8,
    "health_check_broadcast": 600,  # 5min × 2
}


def fetch_ages() -> dict[str, float]:
    """從 /metrics 抓所有 scheduler_job_last_run_age_seconds"""
    try:
        with urllib.request.urlopen("http://localhost:8001/metrics", timeout=10) as r:
            text = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"ERR: /metrics fetch failed: {e}")
        return {}

    ages: dict[str, float] = {}
    for line in text.splitlines():
        if not line.startswith("scheduler_job_last_run_age_seconds{"):
            continue
        # scheduler_job_last_run_age_seconds{job_id="xxx"} value
        try:
            jid = line.split('job_id="')[1].split('"')[0]
            val = float(line.rsplit(" ", 1)[1])
            ages[jid] = val
        except (IndexError, ValueError):
            continue
    return ages


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== Cron Silent Dormant Check ===")

    ages = fetch_ages()
    if not ages:
        print("⚠ no scheduler metrics found — backend may be down or no cron has run yet")
        # 不算 RED — 可能 just restart
        return 0

    print(f"Found {len(ages)} cron job metric(s)")
    print()

    red_jobs: list[str] = []
    unknown_jobs: list[str] = []
    healthy = 0

    for jid, age in sorted(ages.items()):
        threshold = JOB_MAX_AGE.get(jid)
        if threshold is None:
            unknown_jobs.append(jid)
            print(f"  ⚪ {jid:38} age={age/3600:.1f}h (no threshold)")
            continue
        ratio = age / threshold
        if age > threshold:
            red_jobs.append(jid)
            print(f"  🔴 {jid:38} age={age/3600:.1f}h > max {threshold/3600:.1f}h ({ratio:.1f}x)")
        elif age > threshold * 0.5:
            print(f"  🟡 {jid:38} age={age/3600:.1f}h / max {threshold/3600:.1f}h ({ratio:.0%})")
            healthy += 1
        else:
            print(f"  🟢 {jid:38} age={age/3600:.1f}h / max {threshold/3600:.1f}h ({ratio:.0%})")
            healthy += 1

    print()
    print(f"Summary: {healthy} healthy / {len(red_jobs)} RED / {len(unknown_jobs)} unknown")

    if red_jobs:
        print(f"⚠ {len(red_jobs)} cron(s) silent dormant:")
        for j in red_jobs:
            print(f"    - {j}")
        if strict:
            return 1
    else:
        print("✓ all monitored cron within max age")
    return 0


if __name__ == "__main__":
    sys.exit(main())
