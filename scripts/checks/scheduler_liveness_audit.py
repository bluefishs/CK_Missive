"""Scheduler Liveness Audit — 排程真活對賬（2026-06-12，擴大圖譜治理至排程）

擴大治理至排程域（坤哥/Hermes/cron）：排程是 silent dormant 重災區（L52 paths drift、
silent cron 四層防禦等多次 lesson）。「註冊了 ≠ 真的在跑」。

對賬 scheduler.py 註冊 job_id × cron_events.jsonl 實際執行紀錄：
- DORMANT : 註冊但近 N 天無任何執行事件（疑 silent 死 / id 命名不符）
- FAILED  : 最近一次 status=failed
- STALE   : 有跑但最後執行 > 門檻
- 命名不符 : 註冊 id 與 logged job_id 對不上（freshness 檢查會 false-positive）

需在容器內跑（讀 /app/logs/cron_events.jsonl）；host 端 SKIP。

Usage（容器）：
  python /app/scripts/checks/scheduler_liveness_audit.py [--dormant-days 8] [--strict]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def registered_job_ids(scheduler_py: Path) -> set[str]:
    """抓「會發 cron_events 的」job id = @tracked_job('X') 裝飾器 id（實際 emitter，比 add_job id 準）。

    需排除：(a) 註解行；(b) add_job 被註解掉但 tracked_job 還在的（如 shadow_baseline_export
    add_job 已註解=刻意停用）→ 交集 add_job 實際註冊的 id（非註解）才算真排程。
    """
    if not scheduler_py.exists():
        return set()
    tracked: set[str] = set()
    addjob: set[str] = set()
    for line in scheduler_py.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.lstrip().startswith("#"):
            continue
        mt = re.search(r"tracked_job\(['\"]([a-z_0-9]+)['\"]", line)
        if mt:
            tracked.add(mt.group(1))
        ma = re.search(r"id=['\"]([a-z_0-9]+)['\"]", line)
        if ma:
            addjob.add(ma.group(1))
    # 真排程且會發事件 = tracked ∩ add_job（兩者皆非註解）
    return tracked & addjob


def cron_last_runs(jsonl: Path) -> dict[str, tuple[str, str]]:
    """{job_id: (last_ts, last_status)}"""
    last: dict[str, tuple[str, str]] = {}
    if not jsonl.exists():
        return last
    for line in jsonl.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        jid, ts, st = e.get("job_id"), e.get("ts"), e.get("status", "?")
        if jid and ts:
            if jid not in last or ts > last[jid][0]:
                last[jid] = (ts, st)
    return last


def _age_days(ts: str, now: datetime) -> float:
    try:
        return (now - datetime.fromisoformat(ts)).total_seconds() / 86400
    except Exception:
        return 9999


def main(dormant_days: int = 8, strict: bool = False, now_iso: str | None = None) -> int:
    # 容器：scheduler=/app/app/core，cron=/app/logs；host：backend/app/core，backend/logs
    candidates = [
        (Path("/app/app/core/scheduler.py"), Path("/app/logs/cron_events.jsonl")),
        (Path(__file__).resolve().parents[2] / "backend/app/core/scheduler.py",
         Path(__file__).resolve().parents[2] / "backend/logs/cron_events.jsonl"),
    ]
    sched = jsonl = None
    for s, j in candidates:
        if s.exists() and j.exists():
            sched, jsonl = s, j
            break
    if sched is None:
        print("[SKIP] 找不到 scheduler.py + cron_events.jsonl（host 端無 cron 紀錄時正常）")
        return 0

    reg = registered_job_ids(sched)
    runs = cron_last_runs(jsonl)
    if not reg or not runs:
        print(f"[SKIP] 缺 scheduler.py({len(reg)} jobs) 或 cron_events({len(runs)} ran)")
        return 0

    now = datetime.fromisoformat(now_iso) if now_iso else datetime.now()

    dormant, failed, stale = [], [], []
    for jid in sorted(reg):
        if jid not in runs:
            dormant.append(jid)
            continue
        ts, st = runs[jid]
        age = _age_days(ts, now)
        if st != "success":
            failed.append((jid, ts, st))
        elif age > dormant_days:
            stale.append((jid, round(age, 1)))

    # logged 但未註冊（id 命名不符 / 動態 job）
    mismatch = sorted(set(runs) - reg)

    print("=== Scheduler Liveness Audit（排程真活對賬）===")
    print(f"  註冊 job {len(reg)} | 有執行紀錄 job {len(runs)} | dormant {len(dormant)} | "
          f"failed {len(failed)} | stale {len(stale)}\n")
    if dormant:
        print(f"[RED-DORMANT] 註冊但**從無執行事件**（疑 silent 死 / id 不符）：")
        for j in dormant:
            print(f"  ✗ {j}")
        print()
    if failed:
        print("[RED-FAILED] 最近一次執行失敗：")
        for j, ts, st in failed:
            print(f"  ✗ {j:32} {ts} status={st}")
        print()
    if stale:
        print(f"[YELLOW-STALE] 最後執行 > {dormant_days} 天：")
        for j, age in stale:
            print(f"  ~ {j:32} {age} 天前")
        print()
    if mismatch:
        print(f"[INFO] logged 但未註冊 job_id（命名不符或動態）: {', '.join(mismatch)}\n")

    bad = len(dormant) + len(failed)
    print(f"Summary: {len(dormant)} DORMANT, {len(failed)} FAILED, {len(stale)} STALE, "
          f"{len(mismatch)} 命名不符")
    if bad:
        print(f"\n[WARN] {bad} job 未真活 → 查 scheduler 註冊/執行鏈（silent cron dormant）")
        if strict:
            return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dormant-days", type=int, default=8)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    sys.exit(main(dormant_days=args.dormant_days, strict=args.strict))
