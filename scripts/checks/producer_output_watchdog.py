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
    # 2026-07-20 程式圖譜關係健康（抓每日 ingest 洗關係塌陷；健康 ~9670、塌陷 85）
    {"name": "程式圖譜關係", "signal": "db_row_count", "table": "entity_relationships",
     "where": "relation_label='code_graph'", "min": 5000},
]

# 載入共享 JSON registry（不存在則用上方 fallback）
PRODUCER_OUTCOME_REGISTRY = _load_registry()


# ── 契約覆蓋強制（PRODUCER_SELF_CHECK_CONTRACT.md）──
# 已監控 producer：**從 registry 衍生，不再手抄一份**。
#
# 2026-07-31：原本這裡是寫死清單，與 registry 各一份 → 新註冊的
# `case_finance_bridge_selfheal` 明明在 registry 裡（跑出來是 GREEN），
# 覆蓋檢查卻仍把它列為「未納管 blind spot」——**審計自己就是異質同工**
#（同一事實兩處維護，改一處另一處不知道）。改為單一來源衍生。
#
# registry 的 job 識別有兩種寫法：cron_detail 用 "job"，其餘用 "name"（中文）。
# 前者可直接對上 @tracked_job id；後者無法，故另以 _JOB_ALIASES 補上映射。
_JOB_ALIASES = {
    # registry 名稱（中文） → scheduler 的 @tracked_job id
    # 2026-08-02 拆開：兩個 scraper 各自對應自己的 job，不再共用一個信號
    "tender scrape (pcc)": "pcc_today_scrape",
    "tender scrape (ezbid)": "ezbid_cache_refresh",
    "每日覆盤": "daily_self_retrospective",
    "治理儀表板": "governance_dashboard_regen",
    "整合健康E2E": "integration_e2e",
    "晨報": "morning_report",
    "patterns": "memory_pattern_extract",
    "優化管線報告": "optimization_pipeline",
    "週自傳/進化史": "weekly_evolution_generator",
    "wiki 編譯": "wiki_compile",
    "shadow baseline": "shadow_baseline_export",
    "程式圖譜關係": "code_graph_incremental",
    "CF Tunnel 每日驗證": "cf_tunnel_verify",
    "標案業務推薦": "tender_business_recommend",
    # UI 檢核由 Windows 排程執行，非 @tracked_job，不需映射
}


def _monitored_jobs() -> set[str]:
    jobs = set()
    for prod in PRODUCER_OUTCOME_REGISTRY:
        if prod.get("job"):
            jobs.add(prod["job"])
        alias = _JOB_ALIASES.get(prod.get("name", ""))
        if alias:
            jobs.add(alias)
    # 歷史相容：這些 job 的監控信號在別處（見 registry），保留以免誤報
    # 2026-08-02 移除 ezbid_cache_refresh —— 它原本被硬編為「已監控」，理由是
    # 「信號在別處」，但別處那個信號是 pcc+ezbid 合併的，pcc 綠就整體綠。
    # 結果是**兩層各自以為對方在看**，ezbid 死 48 天無人知。現已在 registry 有獨立信號。
    jobs |= {"kg_embedding_backfill", "memory_weekly_autobiography"}
    return jobs


# 非 producer allowlist（稽核/檢查/watchdog/清理/暖機/外部推送/covered-elsewhere——無本地可驗產出）
NON_PRODUCER_JOBS = {
    # 稽核/檢查/watchdog/清理/暖機
    "agent_self_diagnosis", "cf_tunnel_verify", "cleanup_events", "critique_health_audit",
    "cron_outcome_freshness", "cron_self_health_alert", "crystal_review_overdue",
    "embedding_warmup", "fitness_daily", "fitness_weekly", "health_check_broadcast",
    "llm_quota_check", "memory_anti_echo_scan", "process_reminders", "proposal_aging_alert", "security_scan", "tender_dashboard_warm",
    "soul_mirror_sync",
    # 2026-08-03 逐一核實後維持豁免（理由要留在這裡，不是留在 commit message）：
    #   cf_tunnel_verify   — detail 是 {checks_passed, reason}，純驗證結果、
    #                        無業務產出；其失敗已由 fitness cf_tunnel_verify 覆蓋
    #   code_dup_triage    — detail 是 {candidates, true_duplicates}，
    #                        候選為 0 是常態（沒有新重複才是好事），監控會恆為噪音
    "code_dup_triage",
    # 2026-07-18 契約 rollout：圖譜 ingest（健康由 orphan/reconcile step 68 覆蓋）
    "code_graph_incremental", "erp_graph_ingest", "db_graph_refresh",
    # 外部 LINE 推送（產出為外部 LINE，非本地可驗；配額由 line push 邏輯管）
    "daily_self_reflection_line_push", "line_weekly_pulse", "proactive_trigger_scan", "tender_subscription",
    # covered-elsewhere / 非業務產出 / 測試 / L77 死結
    "health_snapshot_log", "memory_crystallization_scan", "synthetic_baseline_inject",
    "tender_pcc_enrichment", "tender_refresh_pending", "ledger_reconciliation",
    "kunge_weekly_learning_summary", "einvoice_sync",
}


# 有 detail 但經人工核實後仍維持豁免者，記下核實日期。
# **不是永久豁免**：超過 EXEMPTION_REVIEW_DAYS 就會再次被列出要求重新核實 ——
# 這整項檢查的存在理由就是「豁免不該寫了就永遠算數」，這裡自然也適用。
REVIEWED_EXEMPTIONS: dict[str, date] = {
    # detail 是 {checks_passed, reason}，純驗證結果、無業務產出；
    # 失敗已由 fitness 的 cf_tunnel_verify 步驟覆蓋
    "cf_tunnel_verify": date(2026, 8, 3),
    # detail 是 {candidates, true_duplicates}；候選為 0 是常態
    #（沒有新重複才是好事），納管會恆為噪音
    "code_dup_triage": date(2026, 8, 3),
}
EXEMPTION_REVIEW_DAYS = 90


def audit_stale_exemptions() -> list[tuple[str, int]]:
    """檢查豁免清單裡是否有 job 其實留下了可驗產出（＝豁免可能已過期）。

    ## 為什麼需要這一項（2026-08-03）

    本檔一直印「✅ 所有 producer 皆已納管（無 blind spot）」，但那個綠燈是
    **靠 38 個手寫豁免撐出來的**：

        53 tracked jobs = 已監控 21 + 非producer 38 + 未納管 0

    而豁免一旦寫進 `NON_PRODUCER_JOBS` 就再也沒有東西複查它還對不對。
    `monthly_arch_review` 正是如此 —— 被歸在「稽核/清理」認定不產出東西，
    於是它的報告送不出去、不落地、detail 全是 None，**三次執行沒人知道**，
    而這支 watchdog 一路報綠。

    降級信號不需要語意判斷：**job 回了 `detail` 就代表它有可驗產出**
    （07-30 契約規則 4：驗證型 job 也必須留下可驗產出），那它就該被監控。

    刻意**不自動移除豁免** —— 那會改變告警行為、也可能誤傷。
    這裡只讓「豁免不再是寫了就永遠算數」。
    """
    if not EVENTS.exists():
        return []
    counts: dict[str, int] = {}
    for line in EVENTS.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        job = ev.get("job_id") or ev.get("job")
        if job in NON_PRODUCER_JOBS and ev.get("detail"):
            # 已核實過的不重複吵，但**核實有效期只有 90 天** ——
            # 否則就是把「豁免永久有效」換個地方再犯一次。
            reviewed = REVIEWED_EXEMPTIONS.get(job)
            if reviewed and (date.today() - reviewed).days < EXEMPTION_REVIEW_DAYS:
                continue
            counts[job] = counts.get(job, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])


def audit_producer_coverage() -> list[str]:
    """讀 scheduler.py 全 @tracked_job，交叉比對 registry + allowlist → 列未納管 producer（blind spot）。"""
    sched = ROOT / "backend" / "app" / "core" / "scheduler.py"
    if not sched.exists():
        return []
    import re
    jobs = set(re.findall(r'@tracked_job\("([a-z_]+)"\)', sched.read_text(encoding="utf-8", errors="ignore")))
    unclassified = sorted(jobs - _monitored_jobs() - NON_PRODUCER_JOBS)
    print("\n" + "-" * 70)
    print(f"契約覆蓋強制：{len(jobs)} tracked jobs = 已監控 {len(jobs & _monitored_jobs())} "
          f"+ 非producer {len(jobs & NON_PRODUCER_JOBS)} + 未納管 {len(unclassified)}")
    if unclassified:
        print("⚠️ 未納管 producer（blind spot，須補註冊信號或加 NON_PRODUCER allowlist）：")
        for j in unclassified:
            print(f"     - {j}")
        print("  → 依 PRODUCER_SELF_CHECK_CONTRACT.md 規則 1/3 分類，防新沉默失敗滋生")
    else:
        print("✅ 所有 producer 皆已納管（無 blind spot）")
    return unclassified


def _job_ran_today(job: str | None) -> bool:
    """該 job 今天是否已執行過（讀 cron_events.jsonl）。

    2026-08-03 立法：`db_table_today` 問「今天有沒有新增」，
    但在 **cron 尚未執行的時段（例如凌晨）必然是 0** ——
    當日 00:33 實跑，pcc/ezbid 兩者都被判 RED，實際只是還沒到執行時間。
    「還沒做」與「做了但沒產出」是完全不同的事，不能都算沉默失敗。
    """
    if not job or not EVENTS.exists():
        return False
    today = date.today().isoformat()
    for line in EVENTS.read_text(encoding="utf-8", errors="ignore").splitlines()[-3000:]:
        if today in line and f'"{job}"' in line:
            return True
    return False


def check_db_table_today(spec: dict) -> tuple[str, str]:
    try:
        import asyncpg, asyncio
    except ImportError:
        return "SKIP", "無 asyncpg"

    # where：讓同一張表能依來源分開監控。
    # 2026-08-02 立法起因：tender_records 原本 pcc+ezbid **合併成一個 producer**，
    # 只要 pcc 有寫入就整體 GREEN → **ezbid 自 06-15 死了 48 天完全隱形**。
    # 一張表餵多個 producer 時，合併監控等於用健康的那個把死掉的那個蓋住。
    where = spec.get("where")
    cond = f"{spec['date_col']}::date = CURRENT_DATE" + (f" AND ({where})" if where else "")
    label = spec["table"] + (f"[{where}]" if where else "")

    async def q():
        conn = await asyncpg.connect(DSN)
        try:
            return await conn.fetchval(f"SELECT COUNT(*) FROM {spec['table']} WHERE {cond}")
        finally:
            await conn.close()

    try:
        n = asyncio.run(q())
    except Exception as e:
        return "SKIP", f"DB 查詢失敗：{str(e)[:60]}"
    if n and n > 0:
        return "GREEN", f"{label} 今日 +{n}"
    if spec.get("weekend_legit") and IS_WEEKEND:
        return "GREEN", f"{label} 今日 0（週末合理空）"
    # 當日 cron 還沒跑過 → 「還沒做」不是「做了沒產出」（見 _job_ran_today 說明）
    job = spec.get("job") or _JOB_ALIASES.get(spec.get("name", ""))
    if not _job_ran_today(job):
        return "SKIP", f"{label} 今日 0（{job or '該 job'} 今日尚未執行，未到判定時機）"
    return "RED", f"{label} 今日 0（今日已執行卻無產出＝疑 producer 沉默失敗）"


def check_db_row_count(spec: dict) -> tuple[str, str]:
    """抓「非零但塌陷」——現有信號的非零檢查抓不到（如關係圖 85 非零但殘缺）。

    2026-07-20 立法：程式圖譜關係曾被每日 incremental job 靜默洗成僅 FK（9669→85），
    85 非零→ db_table_today/cron_detail 皆綠＝漏抓。db_row_count 驗 min 閾值防此類降級。
    """
    try:
        import asyncpg, asyncio
    except ImportError:
        return "SKIP", "無 asyncpg"

    where = spec.get("where", "1=1")

    async def q():
        conn = await asyncpg.connect(DSN)
        try:
            return await conn.fetchval(
                f"SELECT COUNT(*) FROM {spec['table']} WHERE {where}")
        finally:
            await conn.close()

    try:
        n = asyncio.run(q())
    except Exception as e:
        return "SKIP", f"DB 查詢失敗：{str(e)[:60]}"
    if n is not None and n >= spec["min"]:
        return "GREEN", f"{spec['table']}[{where}] = {n}（≥ {spec['min']}）"
    return "RED", f"{spec['table']}[{where}] = {n} < {spec['min']}（疑塌陷/被洗）"


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


def check_json_result(spec: dict) -> tuple[str, str]:
    """讀輸出 JSON 裡的**結果欄位**，不只看檔案有沒有更新。

    2026-08-04 立案：第 5 階（頁面層）的兩支檢核只登記了 `file_fresh` —— 它證明的
    是「檢核器有跑」，不是「頁面是健康的」。實測 `ui-sweep.json` 若 `fail` 由 0 變
    成 25，watchdog 仍然全綠，因為沒有任何人讀那個欄位。這正是本專案反覆立法要
    治的形態：**機制存在 ≠ 閉環成立 —— 它產出的東西，誰收到了？**

    支援的判準（可組合，全部選用）：
      path      檔案路徑；含 `*` 時取**最新**一個相符檔（產出帶時戳者用）
      fail_key  數值或 list，必須為 0 / 空
      min_key   數值，必須 >= min_value（**必要**：只驗 fail=0 會讓「掃到 0 條」也判綠，
                設定寫錯與大面積失效長得一模一樣）
      ok_key    必須為 truthy（布林型產出，如 all_ok）
      expect    {欄位: 期望值} 完全相等（字串型結論，如 overall="PASS"）
      skip_key  只印不判（理由已記在 known_limitations 的跳過屬已知，不製造噪音）
    """
    import json as _json
    raw_path = spec["path"]
    if "*" in raw_path:
        matches = sorted(ROOT.glob(raw_path), key=lambda f: f.stat().st_mtime, reverse=True)
        if not matches:
            return "RED", f"{raw_path} 無相符產出（檢核器沒跑或路徑改了）"
        p = matches[0]
    else:
        p = ROOT / raw_path
        if not p.exists():
            return "RED", f"{raw_path} 不存在（檢核器沒產出）"
    try:
        d = _json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return "RED", f"{p.name} 無法解析: {e}"

    def _count(v):
        return len(v) if isinstance(v, (list, dict)) else int(v or 0)

    parts, reds = [], []

    fail_key = spec.get("fail_key")
    if fail_key:
        n = _count(d.get(fail_key))
        parts.append(f"{fail_key}={n}")
        if n > 0:
            reds.append("有失敗項")

    min_key = spec.get("min_key")
    if min_key:
        n, lo = _count(d.get(min_key)), spec.get("min_value", 0)
        parts.append(f"{min_key}={n}(≥{lo})")
        if n < lo:
            reds.append("通過數低於下限（設定錯或大面積失效都長這樣）")

    ok_key = spec.get("ok_key")
    if ok_key:
        v = d.get(ok_key)
        parts.append(f"{ok_key}={v}")
        if not v:
            reds.append(f"{ok_key} 非真")

    for k, want in (spec.get("expect") or {}).items():
        got = d.get(k)
        parts.append(f"{k}={got}")
        if got != want:
            reds.append(f"{k} 應為 {want}")

    if spec.get("skip_key") is not None:
        parts.append(f"{spec['skip_key']}={d.get(spec['skip_key'])}")

    detail = " ".join(parts)
    if reds:
        return "RED", f"{detail} — {'；'.join(reds)}，看 {p.name}"
    return "GREEN", detail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    print("=" * 70)
    print(f"Producer 產出自我檢核 watchdog（沉默成功偵測 · 標準化架構）{'· 週末' if IS_WEEKEND else ''}")
    print("=" * 70)
    checkers = {"db_table_today": check_db_table_today, "cron_detail": check_cron_detail,
                "file_fresh": check_file_fresh, "db_row_count": check_db_row_count,
                "json_result": check_json_result}
    anomalies = []
    skipped: list[tuple[str, str]] = []
    for spec in PRODUCER_OUTCOME_REGISTRY:
        fn = checkers.get(spec["signal"])
        if not fn:
            continue
        tag, msg = fn(spec)
        print(f"  [{tag:5}] {spec['name']:24} ({spec['signal']}) — {msg}")
        if tag == "RED":
            anomalies.append((spec["name"], msg))
        elif tag == "SKIP":
            skipped.append((spec["name"], msg))

    # 契約覆蓋強制（防新沉默失敗滋生）
    unclassified = audit_producer_coverage()

    stale_exempt = audit_stale_exemptions()
    if stale_exempt:
        print("")
        print(f"⚠️ 豁免可能已過期：{len(stale_exempt)} 個 NON_PRODUCER job 其實留下了 detail")
        for job, n in stale_exempt:
            print(f"     - {job}（{n} 次有 detail）")
        print("  → 有可驗產出就該被監控。請改註冊為 producer，")
        print("     或在 registry 寫明「為何有 detail 仍不需監控」——")
        print("     理由要留在 registry，不是留在某次 commit message 裡。")

    # SKIP ≠ PASS：未驗完必須與通過分開講，否則「20 producer 產出正常」
    # 會把「其中 2 個根本沒驗」一起講成正常（2026-08-03 實際踩到）。
    if skipped:
        print("")
        print(f"⚪ 未驗完 {len(skipped)} 項（不計入正常）：")
        for name, m in skipped:
            print(f"     {name}: {m}")

    print("\n" + "=" * 70)
    verified = len(PRODUCER_OUTCOME_REGISTRY) - len(skipped)
    if not anomalies and not unclassified:
        print(f"GREEN: {verified} producer 產出正常"
              + (f"（另 {len(skipped)} 項未驗完）" if skipped else "")
              + " + 覆蓋無 blind spot")
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
