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


def derive_thresholds_from_scheduler() -> dict[str, int]:
    """讀 scheduler.py 推導 {job_id: max_age_seconds}。讀不到就回空 dict（降級不阻斷）。"""
    sched = Path(__file__).resolve().parents[1].parent / "backend" / "app" / "core" / "scheduler.py"
    if not sched.exists():
        return {}
    try:
        src = sched.read_text(encoding="utf-8", errors="ignore")
    except Exception:
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
    strict = "--strict" in sys.argv
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
    if not derived_n:
        print("⚠ 無法從 scheduler.py 推導週期 —— 僅套用 override，覆蓋率會偏低")
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
