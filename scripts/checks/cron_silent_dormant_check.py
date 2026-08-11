"""Fitness step (v6.12 #2 補完): cron silent dormant 偵測

從 /metrics 讀 scheduler_job_last_run_age_seconds，找 age 超過 normal_interval × 2 的 cron。

設計：
- 不知道 normal interval 的 job → SKIP (前提：每個 job 設 max_age_threshold)
- 已知 interval (cron expression 推算) → 超 threshold = RED
- 配合 fitness daily / weekly 雙頻 forcing

注：每個 cron 該有自己的 SLO interval。本檢查使用保守 threshold 對映表。
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

# host 端 Windows 主控台預設 cp950，印任何非 CJK 符號（⚪ ✓ …）就 UnicodeEncodeError
# → 整支檢核崩潰，fitness 只看得到非 0 exit code、以為是「偵測到 dormant」。
# 2026-08-02：本支是 L49.8 家族第 3 例（前兩支已修，此支漏網）。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # 非 Windows 或已是 utf-8
    pass


# 手動 override（僅限「從 scheduler.py 推導不出來」的情況）。
#
# 2026-08-02 由 20 項縮減為 1 項：這張表原本是**第二份事實**，排程改了它不會跟著改，
# 實際造成 5 支每日 job 天天假警報（v6.26 把 code_graph 改成每日全量，表沒跟著改），
# 另有 3 支的值已與實際排程不符（wiki_lint / einvoice_sync / tender_dashboard_warm）。
# 現在週期一律由 derive_thresholds_from_scheduler() 從 add_job 的 trigger 推導，
# 排程改動自動跟隨；只有推導不出來的才留在這裡。
JOB_MAX_AGE = {
    # IntervalTrigger(minutes=reminder_interval_minutes) —— 週期是設定值，
    # 靜態解析看不到實際數字（推導會保守給 1 天，對 5 分鐘級的 job 太鬆）。
    "process_reminders": 600,  # 5min × 2
}


# ---------------------------------------------------------------------------
# 從 scheduler.py 自動推導閾值（2026-08-02）
#
# 為什麼要做：上面那張手寫表是**第二份事實**，排程改了它不會跟著改。
# 實際後果：v6.26（07-20）把 code_graph 由 15min 增量改成每日 03:00 全量重建，
# 表沒跟著改 → 該 job 每天跑完幾小時就被誤報 dormant，連同另外 4 支共 5 支天天假警報。
# 而且 47 個 cron 只有 15 個在表內，其餘 32 個是 "no threshold"＝根本沒監控。
#
# 作法：解析 add_job 的 trigger 推出實際週期，閾值取 週期×2（沿用原慣例）。
# 推導為主、JOB_MAX_AGE 為 override —— 核對過的 12 項兩者一致，另 4 項推導更貼近實際排程。
# ---------------------------------------------------------------------------
#  id 可能是字面字串，也可能是 f-string（動態註冊多時段，如
#  `id=f'tender_subscription_{hour}'`）。後者在 /metrics 裡的 job_id 是
#  @tracked_job 的名稱（不含後綴），所以取 f-string 的固定前綴並去掉尾端底線。
_ADD_JOB_RE = re.compile(
    r"trigger=(Cron|Interval)Trigger\((?P<args>[^)]*)\).*?id=f?['\"](?P<jid>[a-z0-9_]+)",
    re.S,
)


def _interval_seconds(kind: str, args: str) -> int | None:
    """由 trigger 參數推算執行週期（秒）。無法判定回 None（不猜）。"""
    if kind == "Interval":
        m = re.search(r"minutes=(\d+)", args)
        if m:
            return int(m.group(1)) * 60
        m = re.search(r"hours=(\d+)", args)
        if m:
            return int(m.group(1)) * 3600
        # minutes=變數 → 週期由設定決定，保守以 1 天計（不誤報）
        return 86400 if "minutes=" in args or "hours=" in args else None
    # CronTrigger：由最粗的欄位決定週期
    if "day_of_week" in args:
        return 86400 * 7
    if re.search(r"\bday=", args):
        return 86400 * 30
    if "hour=" in args:
        # hour='*/N' → 每 N 小時；hour=N 或 hour=變數 → 每日
        m = re.search(r"hour=['\"]?\*/(\d+)", args)
        return int(m.group(1)) * 3600 if m else 86400
    if "minute=" in args:
        return 3600
    return None


def _scheduler_path() -> Path | None:
    """找 scheduler.py —— host 與容器的目錄結構不同，兩個都要試。

    2026-08-11：原本只算 host 的相對位置（repo/backend/app/core/scheduler.py）。
    容器內 backend 就是 /app，scripts 掛在 /app/scripts，於是算出
    /app/backend/app/core/scheduler.py —— 不存在，然後 `return {}` **靜默**降級。

    後果不是「少了幾個閾值」而是**整個推導為空**：36 個 cron 全部落到
    "no threshold"，而本支照樣印「✓ all monitored cron within max age」＝
    每天在排程情境下給一個假綠，一路綠到 08-11 才被發現。
    這是 L52（host↔container 路徑）與「沉默降級＝假綠」的交集。
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "backend" / "app" / "core" / "scheduler.py",  # host: <repo>/backend/...
        here.parents[2] / "app" / "core" / "scheduler.py",              # container: /app/app/...
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def derive_thresholds_from_scheduler() -> dict[str, int]:
    """讀 scheduler.py 推導 {job_id: max_age_seconds}。

    讀不到**必須出聲**：閾值為空時本支會把所有 cron 判成 "no threshold" 並印全綠，
    那是「沒有人在監控」而不是「監控通過」——兩者不得長得一樣。
    """
    sched = _scheduler_path()
    if sched is None:
        print("✗ 找不到 scheduler.py —— 無法推導任何閾值，本次不具監控效力（不視為通過）")
        return {}
    try:
        src = sched.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"✗ 讀取 scheduler.py 失敗：{e} —— 無法推導閾值（不視為通過）")
        return {}
    out: dict[str, int] = {}
    for m in _ADD_JOB_RE.finditer(src):
        secs = _interval_seconds(m.group(1), m.group("args"))
        if not secs:
            continue
        jid = m.group("jid").rstrip("_")  # f-string 前綴會留下尾端底線
        # 同名 job 註冊多次（多時段）→ 取最短週期，否則會低估頻率而漏抓
        out[jid] = min(out.get(jid, secs * 2), secs * 2)
    return out


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
    # 2026-08-11：不再看 --strict。呼叫端傳不傳旗標，都依原生三態回退出碼；
    # 「有沒有人在監控」不該由呼叫端的旗標決定。
    print("=== Cron Silent Dormant Check ===")

    ages = fetch_ages()
    if not ages:
        print("⚠ no scheduler metrics found — backend may be down or no cron has run yet")
        # 不算 RED — 可能 just restart
        return 0

    # 推導為主、手寫為 override（見上方說明）
    thresholds = derive_thresholds_from_scheduler()
    derived_n = len(thresholds)
    thresholds.update(JOB_MAX_AGE)
    print(f"Found {len(ages)} cron job metric(s)｜閾值來源：推導 {derived_n} + override {len(JOB_MAX_AGE)}")
    print()

    red_jobs: list[str] = []
    unknown_jobs: list[str] = []
    healthy = 0

    for jid, age in sorted(ages.items()):
        threshold = thresholds.get(jid)
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

    # 2026-08-11：以下三條退出碼語意一併校正（0=GREEN / 1=YELLOW / 2+=RED）。
    #
    # (a) 推導不出任何閾值 = 沒有人在監控，不是監控通過。
    #     在此之前它只印一行 warning 就 return 0，於是容器內每天印
    #     「✓ all monitored cron within max age」而實際監控覆蓋率是 1/37。
    # (b) 大多數 cron 落在 unknown = 覆蓋率退化，要在變成 (a) 之前就出聲。
    # (c) 找到 dormant 卻只在 --strict 時回非 0 —— 就是 L83「印 RED 卻 exit 0」
    #     那一族（08-10 才在 powershell_bom_audit 修過同型）。RED 一律非零。
    if not derived_n:
        print("🔴 未能從 scheduler.py 推導出任何閾值 —— 本次檢核不具監控效力")
        return 2

    if unknown_jobs and len(unknown_jobs) > len(ages) / 2:
        print(f"🟡 {len(unknown_jobs)}/{len(ages)} 個 cron 沒有閾值（覆蓋率 "
              f"{(len(ages) - len(unknown_jobs)) / len(ages):.0%}）—— 推導可能已部分退化")
        return 1

    if red_jobs:
        print(f"🔴 {len(red_jobs)} cron(s) silent dormant:")
        for j in red_jobs:
            print(f"    - {j}")
        return 2

    print("✓ all monitored cron within max age")
    return 0


if __name__ == "__main__":
    sys.exit(main())
