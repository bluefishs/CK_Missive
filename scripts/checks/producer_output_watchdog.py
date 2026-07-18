#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Producer 產出自我檢核 watchdog（Silent-Success Detector）— 行為層 SSOT

★ 立法緣起（2026-07-18）：owner 質疑「圖譜/SSOT 治理多次提出但問題仍反覆」。
  診斷＝反覆的低階問題（KG embedding embedded=0、tender scrape records=0、
  AIConfig silent 降級…）有共同根＝**沉默成功（silent success）**：job 報 success
  但實際產出 0/沒做事，失敗隱形直到人看到症狀。

  為何圖譜/SSOT 抓不到：程式圖譜/DB ER 圖譜/code wiki 都是**結構真相**（系統「是」
  什麼），SSOT audit 抓 config drift/死碼/重複。**沒有一層監控「行為/產出真相」**
  （每個 producer 今天真的產出了嗎）。@tracked_job 只記 status/duration。

  ★ 這是 AI 優勢的落地：系統**自我檢核**——自動抓「我報成功但沒產出且非合理原因」，
  不等人看症狀。producer 各自 self-report reason（見 scheduler.py 各 job 回傳 detail），
  watchdog 聚合判定；隨更多 job 採用 detail+reason 模式，覆蓋自動擴大（自我進化）。

偵測邏輯：讀 cron_events.jsonl，對每個 producer job 的最近 detail：
  - reason ∈ 問題集（fetch_failed / weekday_zero_suspicious / exception / connector_none…）→ RED
  - 產出=0 連續 N 次且無合理原因（legitimate_zero）→ RED（silent success）

host 側執行（讀 backend/logs/cron_events.jsonl，mounted）。cp950 韌性。
用法：
    python scripts/checks/producer_output_watchdog.py
    python scripts/checks/producer_output_watchdog.py --strict   # 有異常 exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "backend" / "logs" / "cron_events.jsonl"

# 明確的「問題原因」——job self-report 到 detail.reason 者，出現即異常
PROBLEM_REASONS = {
    "fetch_failed", "weekday_zero_suspicious", "exception", "connector_none",
    "embedding backend not ready", "no_token", "error",
}

# Producer 註冊表：job_id → {產出欄位, 合理零原因}
# 隨更多 producer 採 detail+reason 模式而擴充（自我進化）。
PRODUCER_REGISTRY = {
    "pcc_today_scrape": {"output": "records", "ok_zero_reasons": {"weekend_no_publish", "ok"}},
    "kg_embedding_backfill": {"output": "embedded", "ok_zero_reasons": {None, "coverage_full"}},
    # 未來擴充：ezbid_cache_refresh / morning_report / tender_business_recommend / line push …
}


def load_recent_events(job_id: str, n: int = 5) -> list[dict]:
    if not EVENTS.exists():
        return []
    rows = []
    try:
        for line in EVENTS.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or job_id not in line:
                continue
            try:
                e = json.loads(line)
                if e.get("job_id") == job_id:
                    rows.append(e)
            except Exception:
                continue
    except Exception:
        return []
    return rows[-n:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    print("=" * 68)
    print("Producer 產出自我檢核 watchdog（沉默成功偵測 — 行為層 SSOT）")
    print("=" * 68)
    if not EVENTS.exists():
        print(f"[SKIP] cron_events 不存在：{EVENTS}")
        return 0

    anomalies = []
    for job_id, spec in PRODUCER_REGISTRY.items():
        events = load_recent_events(job_id, 5)
        if not events:
            print(f"\n[{job_id}] 無近期事件（可能未跑或未記 detail）")
            continue
        latest = events[-1]
        detail = latest.get("detail") or {}
        reason = detail.get("reason")
        out_key = spec["output"]
        out_val = detail.get(out_key)

        # 判定
        problem = None
        if reason in PROBLEM_REASONS:
            problem = f"reason={reason}（job 自報問題）"
        elif out_val == 0 and reason not in spec["ok_zero_reasons"]:
            # 產出 0 且非合理零 → 檢查是否連續
            zeros = sum(1 for e in events if (e.get("detail") or {}).get(out_key) == 0
                        and (e.get("detail") or {}).get("reason") not in spec["ok_zero_reasons"])
            problem = f"{out_key}=0 連續 {zeros}/{len(events)} 次且非合理零（reason={reason}）"

        status = latest.get("status")
        tag = "RED" if problem else "GREEN"
        print(f"\n[{job_id}] status={status} {out_key}={out_val} reason={reason} [{tag}]")
        if problem:
            print(f"     ⚠️ 沉默成功/異常：{problem}")
            print(f"     ts={latest.get('ts')}")
            anomalies.append((job_id, problem))

    print("\n" + "=" * 68)
    if not anomalies:
        print("GREEN: 所有已註冊 producer 產出正常（無沉默成功）")
        print(f"（已監測 {len(PRODUCER_REGISTRY)} producer；隨更多 job 採 detail+reason 模式擴大覆蓋）")
        return 0
    print(f"RED: {len(anomalies)} 個 producer 疑沉默成功/異常：")
    for job, p in anomalies:
        print(f"  - {job}: {p}")
    print("→ 這些是「報 success 但沒產出/失敗」，人不看症狀也能自動抓（AI 自我檢核）")
    if args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
