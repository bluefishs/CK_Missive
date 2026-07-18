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

# ★ Producer Outcome Registry（標準化自我檢核 SSOT）
#   2026-07-18 外部化為共享 JSON（backend/config/producer_outcome_registry.json），
#   host watchdog + in-container cron_outcome_freshness 共讀，避免兩份 registry 漂移（DRY）。
def _load_registry() -> list[dict]:
    cfg = ROOT / "backend" / "config" / "producer_outcome_registry.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            regs = data.get("producers", [])
            for r in regs:  # JSON list → set；JSON null → None（已是）
                if "ok_zero_reasons" in r:
                    r["ok_zero_reasons"] = set(r["ok_zero_reasons"])
            if regs:
                return regs
        except Exception as e:
            print(f"[WARN] registry JSON 載入失敗，用內建 fallback：{e}")
    return _FALLBACK_REGISTRY


_FALLBACK_REGISTRY = [
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
    # 2026-07-18 擴大：更多 producer（前進方向＝運維自主擴大投資）
    {"name": "優化管線報告", "signal": "file_fresh", "path": "wiki/memory/pipeline-reports", "max_h": 30},
    # 週報型（autobiography/weekly_evolution 寫入 evolutions/，週級 cadence → 容許 ~9 日）
    {"name": "週自傳/進化史", "signal": "file_fresh", "path": "wiki/memory/evolutions", "max_h": 216},
    # 2026-07-18 契約 rollout：18 blind spot 逐一分類——註冊清晰 producer
    {"name": "標案業務推薦", "signal": "db_table_today", "table": "tender_recommendation_history",
     "date_col": "pushed_at", "weekend_legit": True},  # 每日09:00，週末無標案合理空
    {"name": "wiki 編譯", "signal": "file_fresh", "path": "wiki/topics", "max_h": 216},  # 週級
    # shadow 輸出＝shadow_trace.db（非空的 shadow-baseline/ 目錄；核實：db 今日活、目錄 legacy 空）
    {"name": "shadow baseline", "signal": "file_fresh", "path": "backend/logs/shadow_trace.db", "max_h": 30},
]

# 載入共享 JSON registry（不存在則用上方 fallback）
PRODUCER_OUTCOME_REGISTRY = _load_registry()


# ── 契約覆蓋強制（PRODUCER_SELF_CHECK_CONTRACT.md）──
# 已監控 producer（registry 有信號的 job_id）
MONITORED_JOBS = {
    "pcc_today_scrape", "ezbid_cache_refresh", "kg_embedding_backfill", "morning_report",
    "daily_self_retrospective", "governance_dashboard_regen", "memory_pattern_extract",
    "optimization_pipeline", "weekly_evolution_generator", "memory_weekly_autobiography",
    # 2026-07-18 契約 rollout 新註冊
    "tender_business_recommend", "wiki_compile", "shadow_baseline_export",
}
# 非 producer allowlist（稽核/檢查/watchdog/清理/暖機/外部推送/covered-elsewhere——無本地可驗產出）
NON_PRODUCER_JOBS = {
    # 稽核/檢查/watchdog/清理/暖機
    "agent_self_diagnosis", "cf_tunnel_verify", "cleanup_events", "critique_health_audit",
    "cron_outcome_freshness", "cron_self_health_alert", "crystal_review_overdue",
    "embedding_warmup", "fitness_daily", "fitness_weekly", "health_check_broadcast",
    "kb_coverage_check", "llm_quota_check", "memory_anti_echo_scan", "monthly_arch_review",
    "process_reminders", "proposal_aging_alert", "security_scan", "tender_dashboard_warm",
    "wiki_lint", "code_dup_triage", "soul_mirror_sync",
    # 2026-07-18 契約 rollout：圖譜 ingest（健康由 orphan/reconcile step 68 覆蓋）
    "code_graph_incremental", "code_graph_reconcile", "erp_graph_ingest", "db_graph_refresh",
    # 外部 LINE 推送（產出為外部 LINE，非本地可驗；配額由 line push 邏輯管）
    "daily_self_reflection_line_push", "line_weekly_pulse", "proactive_trigger_scan", "tender_subscription",
    # covered-elsewhere / 非業務產出 / 測試 / L77 死結
    "health_snapshot_log", "memory_crystallization_scan", "synthetic_baseline_inject",
    "tender_pcc_enrichment", "tender_refresh_pending", "ledger_reconciliation",
    "kunge_weekly_learning_summary", "einvoice_sync",
}


def audit_producer_coverage() -> list[str]:
    """讀 scheduler.py 全 @tracked_job，交叉比對 registry + allowlist → 列未納管 producer（blind spot）。"""
    sched = ROOT / "backend" / "app" / "core" / "scheduler.py"
    if not sched.exists():
        return []
    import re
    jobs = set(re.findall(r'@tracked_job\("([a-z_]+)"\)', sched.read_text(encoding="utf-8", errors="ignore")))
    unclassified = sorted(jobs - MONITORED_JOBS - NON_PRODUCER_JOBS)
    print("\n" + "-" * 70)
    print(f"契約覆蓋強制：{len(jobs)} tracked jobs = 已監控 {len(jobs & MONITORED_JOBS)} "
          f"+ 非producer {len(jobs & NON_PRODUCER_JOBS)} + 未納管 {len(unclassified)}")
    if unclassified:
        print("⚠️ 未納管 producer（blind spot，須補註冊信號或加 NON_PRODUCER allowlist）：")
        for j in unclassified:
            print(f"     - {j}")
        print("  → 依 PRODUCER_SELF_CHECK_CONTRACT.md 規則 1/3 分類，防新沉默失敗滋生")
    else:
        print("✅ 所有 producer 皆已納管（無 blind spot）")
    return unclassified


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

    # 契約覆蓋強制（防新沉默失敗滋生）
    unclassified = audit_producer_coverage()

    print("\n" + "=" * 70)
    if not anomalies and not unclassified:
        print(f"GREEN: {len(PRODUCER_OUTCOME_REGISTRY)} producer 產出正常 + 覆蓋無 blind spot")
        return 0
    if not anomalies:
        print(f"GREEN(產出): {len(PRODUCER_OUTCOME_REGISTRY)} producer 皆正常；"
              f"⚠️ 但 {len(unclassified)} 未納管 producer 待分類（見上，非產出異常）")
        return 1 if args.strict else 0
    print(f"RED: {len(anomalies)} producer 疑沉默成功/產出異常：")
    for name, m in anomalies:
        print(f"  - {name}: {m}")
    print("→ 系統自動抓「報成功但沒產出/失敗」，不等人看症狀（AI 自我檢核）")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
