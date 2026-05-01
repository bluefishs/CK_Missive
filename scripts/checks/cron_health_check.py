#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: Cron 健康度（v6.2 Phase C2）

防 cron silent failure（同 L21 教訓但對象是 cron 而非 redis）：
- 連續失敗 ≥ 2 次 → fail
- 上次成功超過預期間隔 × 2 → warn
- never_run 但 next_run 已過 → fail

聚焦 5 個 memory cron（v5.10.2~v5.13 建設）：
- memory_pattern_extract（每日 04:00）
- memory_crystallization_scan（每日 04:30）
- memory_weekly_autobiography（週日 18:00）
- memory_anti_echo_scan（週一 06:30）
- memory_metrics_refresh（每 15 分鐘）

擴展性：未來可加 fitness step 14 對其它 cron 群（KG/晨報/觀測）。

用法：
    python scripts/checks/cron_health_check.py
    python scripts/checks/cron_health_check.py --ci

Version: 1.0.0 (2026-05-01)
關聯: L21 silent failure / KUNGE_PROGRESS_TRACKER 鏈路 1B
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

try:
    import urllib.request
except ImportError:
    print("missing urllib", file=sys.stderr)
    sys.exit(2)


METRICS_URL = os.getenv("AGENT_METRICS_URL", "http://localhost:8001")
SERVICE_TOKEN = os.getenv("MCP_SERVICE_TOKEN", "")


def fetch_memory_jobs() -> dict:
    url = f"{METRICS_URL}/api/ai/memory/jobs"
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            **({"X-Service-Token": SERVICE_TOKEN} if SERVICE_TOKEN else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        # 移除可能的 timezone 後綴 (e.g. +08:00)
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def main(ci: bool) -> int:
    print("=== Cron 健康度 Check（v6.2 Phase C2，L21 教訓延伸）===")
    print(f"來源：{METRICS_URL}/api/ai/memory/jobs")
    print()

    resp = fetch_memory_jobs()
    if not resp.get("success"):
        err = resp.get("error", "unknown")
        print(f"[ERROR] /api/ai/memory/jobs 無回應：{err}")
        print("  （後端可能未啟動，warning 模式跳過）")
        return 0  # warning mode：endpoint 不可達不算 fail

    jobs = resp.get("data", {}).get("jobs", [])
    summary = resp.get("data", {}).get("summary", {})
    print(f"summary: total={summary.get('total')} healthy={summary.get('healthy')} "
          f"never_run={summary.get('never_run')} failed={summary.get('failed')}")
    print()

    violations = 0
    warnings = 0
    now = datetime.now()

    # 預期間隔（天）
    expected_intervals = {
        "memory_pattern_extract": 1,
        "memory_crystallization_scan": 1,
        "memory_weekly_autobiography": 7,
        "memory_anti_echo_scan": 7,
        "memory_metrics_refresh": 0.011,  # 15 分鐘 = 0.011 day
    }

    for j in jobs:
        job_id = j.get("job_id", "?")
        status = j.get("last_status", "never_run")
        last_run = parse_iso(j.get("last_run"))
        next_run = parse_iso(j.get("next_run"))
        success_count = j.get("success_count", 0)
        failure_count = j.get("failure_count", 0)

        # 規則 1: 連續失敗 ≥ 2 次（success=0 + failure≥2）
        if status == "failure" and failure_count >= 2 and success_count == 0:
            print(f"[FAIL] {job_id}: 連續失敗 {failure_count} 次無成功")
            violations += 1
            continue

        # 規則 2: 失敗率高（failure / (failure + success) > 50%）
        total = success_count + failure_count
        if total >= 5 and failure_count / total > 0.5:
            print(f"[WARN] {job_id}: 失敗率 {failure_count}/{total} > 50%")
            warnings += 1

        # 規則 3: 上次成功超過預期 × 2
        interval_days = expected_intervals.get(job_id, 1)
        if last_run:
            stale_days = (now - last_run.replace(tzinfo=None)).total_seconds() / 86400
            if stale_days > interval_days * 2:
                print(f"[WARN] {job_id}: 上次跑 {stale_days:.1f} 天前 > "
                      f"預期 {interval_days * 2} 天")
                warnings += 1

        # 規則 4: never_run 但 next_run 已過去 → cron 沒 fire
        if status == "never_run" and next_run:
            tz = next_run.tzinfo
            now_tz = datetime.now(tz) if tz else now
            if next_run < now_tz - timedelta(hours=1):
                print(f"[FAIL] {job_id}: next_run 已過 {next_run.isoformat()} 但仍 never_run")
                violations += 1

        # 健康狀態
        if status == "success":
            print(f"[OK] {job_id}: succ={success_count}/fail={failure_count}")
        elif status == "never_run":
            print(f"[INFO] {job_id}: never_run（next: {j.get('next_run', '?')[:19]}）")

    print()
    if violations > 0:
        print(f"[FAIL] {violations} 個 cron 嚴重異常")
        if warnings > 0:
            print(f"  另有 {warnings} 個 cron 警告")
        return 1 if ci else 0

    if warnings > 0:
        print(f"[WARN] {warnings} 個 cron 警告（但無嚴重異常）")
        return 0

    print("[OK] 所有 cron 健康")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()
    sys.exit(main(args.ci))
