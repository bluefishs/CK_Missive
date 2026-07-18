#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Producer 產出自我檢核 watchdog（Silent-Success Detector）— 行為層 SSOT ★標準化架構

★ 立法（2026-07-18）：owner「圖譜/SSOT 多次提出但問題仍反覆，重點是自我檢核與進化＝AI 優勢」。
  診斷＝反覆低階問題共同根＝**沉默成功**：job 報 success 但產出 0/沒做事，失敗隱形。
  結構圖譜（code/ER/wiki）＝系統「是」什麼；**缺行為層＝系統「做」了什麼/真的產出了嗎**。

★ 標準化自我檢核架構（registry 驅動、多信號型）——scalable + 自我進化：
  與其手動改 40 個 job（不 scalable、又是人工 toil），改用**獨立驗證產出信號**
  （不需信任 job 自報成功）。新增 producer = 加一筆 registry，不動 job → 自我進化。

  3 種產出信號：
  - db_table_today：獨立驗證目標表今日有新增（最 robust，抓「報成功但沒寫入」）
  - cron_detail：job self-report 的 detail[key]（jobs 已回 dict → @tracked_job 記錄）
  - file_fresh：輸出檔/目錄新鮮度（已由 scheduler cron_outcome_freshness 覆蓋，此處登記對照）

host 側執行（DB localhost:5434 + backend/logs/cron_events.jsonl）。cp950 韌性。
用法：
    python scripts/checks/producer_output_watchdog.py
    python scripts/checks/producer_output_watchdog.py --strict   # 有異常 exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "backend" / "logs" / "cron_events.jsonl"
DSN = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"
IS_WEEKEND = date.today().weekday() >= 5

# job self-report 到 detail.reason 的問題原因（出現即異常）
PROBLEM_REASONS = {"fetch_failed", "weekday_zero_suspicious", "exception", "connector_none", "no_token", "error"}

# ★ Producer Outcome Registry（標準化自我檢核 SSOT）——新增 producer 只加一筆
#   signal: db_table_today | cron_detail | file_fresh
PRODUCER_OUTCOME_REGISTRY = [
    # === tender 資料 producer（獨立驗證表增長，最 robust；週末政府不發標＝合理空）===
    {"name": "tender scrape (pcc+ezbid)", "signal": "db_table_today",
     "table": "tender_records", "date_col": "created_at", "weekend_legit": True},
    # === KG embedding（job 自報 embedded；0 合理若覆蓋率已滿）===
    {"name": "kg_embedding_backfill", "signal": "cron_detail", "job": "kg_embedding_backfill",
     "key": "embedded", "ok_zero_reasons": {None, "coverage_full"}},
    # === PCC 爬蟲 self-report（區分週末/失敗）===
    {"name": "pcc_today_scrape", "signal": "cron_detail", "job": "pcc_today_scrape",
     "key": "records", "ok_zero_reasons": {"weekend_no_publish", "ok"}},
    # === 電子發票同步（獨立驗證表；無週末豁免，MOF 每日）===
    # 註：einvoice 表名待確認後啟用；先登記結構
    # {"name": "einvoice_sync", "signal": "db_table_today", "table": "expense_invoices", "date_col": "created_at"},
    # === file producer（已由 scheduler cron_outcome_freshness 每日檢；此處對照登記）===
    {"name": "每日覆盤", "signal": "file_fresh", "path": "wiki/memory/self-retrospective-reports", "max_h": 28},
    {"name": "治理儀表板", "signal": "file_fresh", "path": "docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md", "max_h": 28},
    {"name": "整合健康E2E", "signal": "file_fresh", "path": "wiki/memory/integration-health", "max_h": 28},
    {"name": "晨報", "signal": "file_fresh", "path": "wiki/memory/diary", "max_h": 30},
    {"name": "patterns", "signal": "file_fresh", "path": "wiki/memory/patterns", "max_h": 30},
]


def check_db_table_today(spec: dict) -> tuple[str, str]:
    try:
        import asyncpg, asyncio
    except ImportError:
        return "SKIP", "無 asyncpg"

    async def q():
        conn = await asyncpg.connect(DSN)
        try:
            return await conn.fetchval(
                f"SELECT COUNT(*) FROM {spec['table']} WHERE {spec['date_col']}::date = CURRENT_DATE")
        finally:
            await conn.close()

    try:
        n = asyncio.run(q())
    except Exception as e:
        return "SKIP", f"DB 查詢失敗：{str(e)[:60]}"
    if n and n > 0:
        return "GREEN", f"{spec['table']} 今日 +{n}"
    if spec.get("weekend_legit") and IS_WEEKEND:
        return "GREEN", f"{spec['table']} 今日 0（週末合理空）"
    return "RED", f"{spec['table']} 今日 0（非合理空＝疑 producer 沉默失敗）"


def check_cron_detail(spec: dict) -> tuple[str, str]:
    if not EVENTS.exists():
        return "SKIP", "無 cron_events"
    latest = None
    for line in EVENTS.read_text(encoding="utf-8", errors="ignore").splitlines()[-3000:]:
        line = line.strip()
        if not line or spec["job"] not in line:
            continue
        try:
            e = json.loads(line)
            if e.get("job_id") == spec["job"]:
                latest = e
        except Exception:
            continue
    if not latest:
        return "SKIP", "無近期事件"
    d = latest.get("detail") or {}
    reason = d.get("reason")
    val = d.get(spec["key"])
    if reason in PROBLEM_REASONS:
        return "RED", f"reason={reason}（job 自報問題）"
    if val == 0 and reason not in spec.get("ok_zero_reasons", set()):
        return "RED", f"{spec['key']}=0 非合理零（reason={reason}）"
    return "GREEN", f"{spec['key']}={val} reason={reason}"


def check_file_fresh(spec: dict) -> tuple[str, str]:
    import time
    p = ROOT / spec["path"]
    try:
        if p.is_dir():
            files = list(p.glob("*.md")) + list(p.glob("*.json"))
            newest = max((f.stat().st_mtime for f in files), default=0)
        else:
            newest = p.stat().st_mtime if p.exists() else 0
    except Exception as e:
        return "SKIP", f"{e}"
    age_h = (time.time() - newest) / 3600 if newest else 9999
    if age_h <= spec["max_h"]:
        return "GREEN", f"{age_h:.0f}h 前（門檻 {spec['max_h']}h）"
    return "RED", f"{age_h:.0f}h 前 > 門檻 {spec['max_h']}h（產出 stale）"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    print("=" * 70)
    print(f"Producer 產出自我檢核 watchdog（沉默成功偵測 · 標準化架構）{'· 週末' if IS_WEEKEND else ''}")
    print("=" * 70)
    checkers = {"db_table_today": check_db_table_today, "cron_detail": check_cron_detail, "file_fresh": check_file_fresh}
    anomalies = []
    for spec in PRODUCER_OUTCOME_REGISTRY:
        fn = checkers.get(spec["signal"])
        if not fn:
            continue
        tag, msg = fn(spec)
        print(f"  [{tag:5}] {spec['name']:24} ({spec['signal']}) — {msg}")
        if tag == "RED":
            anomalies.append((spec["name"], msg))

    print("\n" + "=" * 70)
    if not anomalies:
        print(f"GREEN: {len(PRODUCER_OUTCOME_REGISTRY)} producer 產出皆正常（無沉默成功）")
        return 0
    print(f"RED: {len(anomalies)} producer 疑沉默成功/產出異常：")
    for name, m in anomalies:
        print(f"  - {name}: {m}")
    print("→ 系統自動抓「報成功但沒產出/失敗」，不等人看症狀（AI 自我檢核）")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
