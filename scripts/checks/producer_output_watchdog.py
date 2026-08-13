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
    python scripts/checks/producer_output_watchdog.py --strict   # 旗標保留相容，退出碼不再受它影響
    # 退出碼：0=GREEN／1=YELLOW（有未納管 producer）／2=RED（產出異常）
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

# job self-report 到 detail.reason 的問題原因 → 已移入 producer_registry.PROBLEM_REASONS
# （原本 host 與容器各定義一份，改一邊另一邊不會知道）

# ★ Producer Outcome Registry（標準化自我檢核 SSOT）
#   2026-07-18 外部化為共享 JSON（backend/config/producer_outcome_registry.json），
#   host watchdog + in-container cron_outcome_freshness 共讀，避免兩份 registry 漂移（DRY）。
# 2026-08-05：載入與判定改用共用模組 scripts/checks/producer_registry.py。
#
# 原本這裡自己 load JSON，且在讀不到時**靜靜**退回一份內建 `_FALLBACK_REGISTRY`
#（07-18 的舊副本，只有 15 筆，還含著 08-02 已證實會遮蔽 ezbid 死亡 48 天的
# 「pcc+ezbid 合併監控」）。也就是說：registry 一旦消失或壞掉，這支專門偵測
# 沉默失敗的工具會拿一份已知有缺陷的清單繼續印綠燈。那份 fallback 已刪除 ——
# 第二份副本正是它自己的註解在警告的漂移。
try:
    from producer_registry import (
        PROBLEM_REASONS, RegistryUnavailable, build_count_sql, judge, load_registry,
    )
except ImportError:  # 從別的工作目錄呼叫時
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from producer_registry import (
        PROBLEM_REASONS, RegistryUnavailable, build_count_sql, judge, load_registry,
    )

try:
    PRODUCER_OUTCOME_REGISTRY = load_registry(
        ROOT / "backend" / "config" / "producer_outcome_registry.json"
    )
except RegistryUnavailable as _e:
    print(f"✗ 未驗完：{_e}")
    print("（registry 不可用時一律 exit 2，不會退回舊清單假裝檢查過）")
    sys.exit(2)



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
    # 2026-08-05 更正：實際 job id 是 integration_e2e_validation。
    # 原本寫 integration_e2e —— 對應不到任何 job，等於這條別名一直是空的
    # （而因為上面的 regex 也漏掉它，兩個錯誤互相掩護，看起來毫無異狀）。
    "整合健康E2E": "integration_e2e_validation",
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


# 非 producer allowlist —— 2026-08-13 由 `set` 改為 `dict`，每一項必須寫理由。
#
# ## 為什麼改
#
# 原本是個沒有理由欄位的 set。本檔自己的註解早就寫著
# 「豁免一旦寫進來就再也沒有東西複查它還對不對」—— 但只做了一半：
# `audit_stale_exemptions` 抓得到「豁免卻留下 detail」的，抓不到
# 「當初憑什麼認為它不需要證明」。於是 31 個豁免撐起「0 blind spot」的綠燈，
# 而沒有任何地方記著那 31 個判斷的依據。
#
# owner 2026-08-13：「到底還有多少潛藏沉默成本」——
# 這份清單是唯一能把估不出的總量變成**有限具體清單**的地方。
#
# ## 理由怎麼寫才算數
#
# 必須回答：**它壞掉時，症狀是什麼？**
# 若答案是「會有某個東西不見／不動／變舊」，那就是可驗產出 → **不該豁免**，
# 該註冊為 producer。答不出來的，就是還沒想清楚。
#
# 逐項寫過之後，有 5 個當場現形（見下方 SHOULD_BE_PRODUCER）。
NON_PRODUCER_JOBS: dict[str, str] = {
    # ── 檢核／watchdog：產出是「判斷」，判斷本身由它的退出碼與上層 runner 承接 ──
    "agent_self_diagnosis":
        "坤哥自我診斷。壞掉的症狀由 weekly agent_evolution_health 直接查同一批指標，"
        "不必再要求它自己留證據（兩者都紅才是真的）。",
    "cf_tunnel_verify":
        "detail 是 {checks_passed, reason}，純驗證結果無業務產出；"
        "結果檔另由 json_result 納管，失敗會從那裡出聲。",
    "cron_outcome_freshness":
        "檢核的檢核。它壞掉的症狀＝沉默失敗沒人報，而那正是本 watchdog 自己在做的事 —— "
        "由本檔在 host 端獨立執行構成互為備援，不該互相要求對方留產出。",
    "cron_self_health_alert":
        "同 cron_outcome_freshness：告警管道的健康由 credential_liveness_audit（憑證）"
        "與 line 配額計數承接。",
    "critique_health_audit":
        "每兩週寫一個 marker 檔。marker 存在與否本身就是產出，"
        "但它刻意寫在 critiques/_health/ 以免被算成真 critique（2026-08-05 修）—— "
        "由 diary_density_audit 看真 critique 的節奏，不看 marker。",
    "crystal_review_overdue":
        "提醒 owner 有逾期未審提案。0 筆逾期是常態且是好事，納管會恆為噪音；"
        "真正該看的是 proposal 存量本身（已由『結晶提案』producer 納管）。",
    "code_dup_triage":
        "detail 是 {candidates, true_duplicates}；候選為 0 是常態（沒有新重複才是好事），"
        "納管會恆為噪音。",

    # ── 圖譜 ingest：產出是圖上的邊，而邊的健康由專門的稽核看 ──
    "code_graph_incremental":
        "產出是 code graph 的邊。壞掉的症狀＝邊數塌陷或 orphan 累積，"
        "已由『程式圖譜關係』的 db_row_count（min 5000）與 weekly orphan/reconcile 覆蓋 —— "
        "那比 job 自己回報的筆數可靠（2026-07-20 就是靠 row count 抓到每日洗圖的 bug）。",
    "erp_graph_ingest":
        "同 code_graph_incremental，產出併入同一張圖的 row count 監測。",
    "db_graph_refresh":
        "同上；schema 反射的結果落在同一張圖。",

    # ── 外部推送：產出離開本機，本地留不下可驗證據 ──
    "daily_self_reflection_line_push":
        "產出是送到 LINE 的訊息，本地無法驗證對方收到。"
        "推播管道的健康由 credential_liveness_audit（token 存活）與月配額計數承接。",
    "line_weekly_pulse": "同上。",
    "proactive_trigger_scan":
        "夜間吹哨者：掃描結果進 line_digest_buffer，由晨報一次送出 —— "
        "產出的接收者是晨報而非本地檔案；晨報本身已納管。",
    "tender_subscription":
        "標案訂閱推播。同 LINE 族；另 owner 已關閉即時推播（TENDER_SUB_LINE_REALTIME），"
        "此時 0 推送是政策性合理空，納管會誤報。",

    # ── 暖機／快取：產出是「下一次比較快」，沒有可驗的落地物 ──
    "embedding_warmup":
        "把模型載進記憶體。壞掉的症狀是首次查詢變慢，屬效能不屬正確性；"
        "真的失效會在 shadow_baseline 的 p95 上顯現。",
    "tender_dashboard_warm":
        "預熱標案儀表板快取。壞掉的症狀是使用者第一次開比較慢，資料本身仍正確；"
        "資料面的健康由 tender_freshness_audit 覆蓋。",

    # ── 清理：產出是「東西變少」，而變少沒有下限可訂 ──
    "cleanup_events":
        "清理過期事件。壞掉的症狀是 cron_events.jsonl 無限增長 —— "
        "⚠️ 這其實可觀測（檔案大小），只是目前沒有人在看。列為待升級候選。",

    # ── 其他 ──
    "health_check_broadcast":
        "每 5 分鐘檢查各服務健康並在異常時推播。無異常時本來就不該有產出；"
        "服務本身的健康由五系統公網探針與容器 healthcheck 承接。",
    "health_snapshot_log":
        "把當下健康寫進 log 供事後追溯。log 本身就是產出，"
        "但它的價值在出事後回查，平時要求它證明自己會產生噪音。",
    "llm_quota_check":
        "檢查 LLM 配額。額度充足時無產出；不足時走 digest。"
        "憑證與配額的存活由 credential_liveness_audit 承接。",
    "memory_anti_echo_scan":
        "反回音掃描：抓記憶裡自我引用造成的假成長。0 命中是常態且是好事。",
    "proposal_aging_alert":
        "提案老化告警。0 筆逾期是常態；提案存量本身已由『結晶提案』producer 納管。",
    "security_scan":
        "⚠️ 它其實會產出 issues 數（實測掃到 9 issues），"
        "只是沒有回 detail。列為待升級候選。",
    "soul_mirror_sync":
        "SOUL.md 跨 repo 同步。漂移由 weekly soul_mirror_drift_check 直接比對兩份檔案 —— "
        "那比 job 自己說「我同步了」可靠。",
    "synthetic_baseline_inject":
        "注入合成查詢以維持 baseline 樣本量。產出是 shadow_trace 的列，"
        "而 baseline 的健康由 shadow_baseline_* 五個 gauge 承接。",
    "process_reminders":
        "⚠️ 它其實會產出 {total, sent, failed, retries}（log 裡看得到），"
        "只是沒有回 detail。列為待升級候選。",
    "tender_pcc_enrichment":
        "PCC 詳情補完。L77 已確證資料源存在死結（org_id 只在被反爬限流的頁面），"
        "取不到是已知且無解的常態，納管等於每天報一次已知問題。",
    "tender_refresh_pending":
        "重試先前失敗的標案抓取。0 筆待重試是常態且是好事。",
    "ledger_reconciliation":
        "⚠️ 帳本對帳。對得上時無產出，但『對不上幾筆』是明確可回報的數字。"
        "列為待升級候選。",
    "kunge_weekly_learning_summary":
        "週學習摘要，產出走 LINE digest；學習閉環的實質產出"
        "（patterns/proposals/crystals）已於 2026-08-05 各自納管。",
    "einvoice_sync":
        "⚠️ 財政部電子發票同步，會產出同步筆數。目前 MOF_APP_ID 未設定故從未註冊，"
        "但一旦啟用就是不折不扣的 producer。列為待升級候選（啟用時必須同時註冊）。",
}

# 逐項寫理由時當場現形的 —— 它們**有可驗產出**，只是還沒回 detail。
# 不立刻改成 producer 是因為那需要動 scheduler 並 rebuild；
# 列在這裡讓它們不會再度隱形，下次動 backend 時一併處理。
SHOULD_BE_PRODUCER = {
    "process_reminders": "已有 {total, sent, failed, retries}，只是沒回傳",
    "security_scan": "已有 issues 數，只是沒回傳",
    "ledger_reconciliation": "『對不上幾筆』是明確數字",
    "cleanup_events": "清了幾筆／檔案大小是可觀測的",
    "einvoice_sync": "啟用後即為 producer，啟用時必須同時註冊",
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
    # 2026-08-05：regex 補上數字。原本是 `[a-z_]+`，於是含數字的 job id
    # （`integration_e2e_validation` 的 e2e）**從來不在這個稽核的視野裡** ——
    # 既不會被算成已監控，也不會被列為 blind spot，就是不存在。
    # 一支稽核把「認不得的東西」靜靜排除，就會一路印「0 blind spot」。
    jobs = set(re.findall(r'@tracked_job\("([a-z0-9_]+)"\)',
                          sched.read_text(encoding="utf-8", errors="ignore")))
    unclassified = sorted(jobs - _monitored_jobs() - set(NON_PRODUCER_JOBS))
    print("\n" + "-" * 70)
    print(f"契約覆蓋強制：{len(jobs)} tracked jobs = 已監控 {len(jobs & _monitored_jobs())} "
          f"+ 非producer {len(jobs & set(NON_PRODUCER_JOBS))} + 未納管 {len(unclassified)}")
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
    label = spec["table"] + (f"[{where}]" if where else "")

    async def q():
        conn = await asyncpg.connect(DSN)
        try:
            return await conn.fetchval(build_count_sql(spec))
        finally:
            await conn.close()

    try:
        n = asyncio.run(q())
    except Exception as e:
        return "SKIP", f"DB 查詢失敗：{str(e)[:60]}"

    # 「還沒做」不是「做了沒產出」——這是**環境層**判斷（今天到了沒），
    # 留在呼叫端；紅綠裁決一律交給共用的 judge()。
    if not n and not (spec.get("weekend_legit") and IS_WEEKEND):
        job = spec.get("job") or _JOB_ALIASES.get(spec.get("name", ""))
        if not _job_ran_today(job):
            return "SKIP", f"{label} 今日 0（{job or '該 job'} 今日尚未執行，未到判定時機）"

    problem = judge(spec, is_weekend=IS_WEEKEND, db_value=n)
    if problem:
        return "RED", f"{label} 今日 0（今日已執行卻無產出＝疑 producer 沉默失敗）"
    if n:
        return "GREEN", f"{label} 今日 +{n}"
    return "GREEN", f"{label} 今日 0（週末合理空）"


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
            return await conn.fetchval(build_count_sql(spec))
        finally:
            await conn.close()

    try:
        n = asyncio.run(q())
    except Exception as e:
        return "SKIP", f"DB 查詢失敗：{str(e)[:60]}"

    problem = judge(spec, db_value=n)
    if problem:
        return "RED", f"{spec['table']}[{where}] = {n} < {spec['min']}（疑塌陷/被洗）"
    return "GREEN", f"{spec['table']}[{where}] = {n}（≥ {spec['min']}）"


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
    problem = judge(spec, latest_event=latest)
    if problem:
        return "RED", problem.split(": ", 1)[-1]
    return "GREEN", f"{spec['key']}={d.get(spec['key'])} reason={d.get('reason')}"


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
    problem = judge(spec, newest_mtime=newest)
    if problem:
        return "RED", f"{age_h:.0f}h 前 > 門檻 {spec['max_h']}h（產出 stale）"
    return "GREEN", f"{age_h:.0f}h 前（門檻 {spec['max_h']}h）"


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

    # parts 只負責**呈現**（讓人看得到每個判準的實際值），
    # 紅綠裁決一律交給共用的 judge() —— 先前這裡與容器端各判一次。
    parts = []
    if spec.get("fail_key"):
        parts.append(f"{spec['fail_key']}={_count(d.get(spec['fail_key']))}")
    if spec.get("min_key"):
        parts.append(
            f"{spec['min_key']}={_count(d.get(spec['min_key']))}"
            f"(≥{spec.get('min_value', 0)})"
        )
    if spec.get("ok_key"):
        parts.append(f"{spec['ok_key']}={d.get(spec['ok_key'])}")
    for k in (spec.get("expect") or {}):
        parts.append(f"{k}={d.get(k)}")
    if spec.get("skip_key") is not None:
        parts.append(f"{spec['skip_key']}={d.get(spec['skip_key'])}")

    detail = " ".join(parts)
    problem = judge(spec, json_files=[p])
    if problem:
        return "RED", f"{detail} — {problem.split(': ', 1)[-1]}，看 {p.name}"
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

    # 2026-08-13：豁免清單改為帶理由後，有 5 項在寫理由的當下現形 ——
    # 它們**有可驗產出，只是沒回傳 detail**。寫在註解裡等於沒說，必須印出來，
    # 否則下次還是只會看到「0 blind spot」的綠燈。
    # 刻意不判紅：它們現在的狀態與昨天一樣，紅一個「早就存在且已知」的東西
    # 只會製造噪音；但它必須是可見的，直到有人動 scheduler 把 detail 補上。
    if SHOULD_BE_PRODUCER:
        print("")
        print(f"📋 豁免中但其實有可驗產出（{len(SHOULD_BE_PRODUCER)} 項，"
              f"下次動 backend 時一併補 detail 並註冊）：")
        for job, why in SHOULD_BE_PRODUCER.items():
            print(f"     {job}: {why}")

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
    # 2026-08-12：退出碼不再看 --strict，改依原生三態（0=GREEN／1=YELLOW／2+=RED）。
    # 這是 L83「印 RED 卻 exit 0」家族的第三例 —— 前兩例（08-07
    # doc_baseline_claim_audit、08-10 powershell_bom_audit）修的時候都立過同一條規矩，
    # 而這支漏改。它在 run_fitness.sh 裡剛好帶了 --strict 所以排程情境沒出事，
    # 但任何不帶旗標的呼叫端（人工複查、別的 runner）拿到的是
    # 「畫面印著 RED、退出碼卻說通過」—— 嚴重度不該由呼叫端的旗標決定。
    if not anomalies:
        print(f"GREEN(產出): {len(PRODUCER_OUTCOME_REGISTRY)} producer 皆正常；"
              f"⚠️ 但 {len(unclassified)} 未納管 producer 待分類（見上，非產出異常）")
        return 1
    print(f"RED: {len(anomalies)} producer 疑沉默成功/產出異常：")
    for name, m in anomalies:
        print(f"  - {name}: {m}")
    print("→ 系統自動抓「報成功但沒產出/失敗」，不等人看症狀（AI 自我檢核）")
    return 2


if __name__ == "__main__":
    sys.exit(main())
