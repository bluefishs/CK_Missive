"""Fitness step (v6.12 #2 補完): cron silent dormant 偵測

從 /metrics 讀 scheduler_job_last_run_age_seconds，找 age 超過 normal_interval × 2 的 cron。

設計：
- 不知道 normal interval 的 job → SKIP (前提：每個 job 設 max_age_threshold)
- 已知 interval (cron expression 推算) → 超 threshold = RED
- 配合 fitness daily / weekly 雙頻 forcing

注：每個 cron 該有自己的 SLO interval。本檢查使用保守 threshold 對映表。
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime
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


def cannot_judge(age: float, threshold: float, uptime: float) -> str | None:
    """說不準的時候回傳理由字串，說得準回 None。

    **這條規則有兩條路徑在用**（metrics 與持久紀錄）。寫成函式不是為了漂亮，
    是因為 2026-08-15 第一版只改了其中一邊，出現「同樣說不準的兩支，
    一支豁免一支判紅」—— 靠 NameError 當場炸出來才發現。

    兩個守則缺一不可：

    1. **扣掉重啟後的時間**：重啟會重置 IntervalTrigger，下一次 fire 是
       「重啟時刻 + 週期」，所以重啟後那段沉默是必然的。
       但重啟**只解釋得了重啟之後那一段** —— 已經沉默 200 小時的 job，
       剛重啟也不該變綠，所以是扣除不是豁免。
    2. **行程還沒開機夠久到能跑一次**：門檻是週期的兩倍（見 derive），
       所以 `uptime < threshold/2` 代表這個 incarnation 裡它連一次機會都還沒有。
       需要這條是因為 **uptime 只反映最後一次重啟** —— 一天內連續 rebuild 時，
       扣除額被歸零而 age 持續累積，光靠守則 1 每次 rebuild 都會製造數小時假紅。

       但守則 2 有**上限**：`age >= threshold × 2` 就不再適用。
       重啟churn 每次最多只能解釋約一個週期的沉默，
       超過門檻兩倍的沉默不是重啟解釋得了的 ——
       少了這個上限，一支真的死掉 200 小時的 job 會在重啟後被判成綠的
       （六情境測試第 3 案當場抓到，那比假紅嚴重得多）。

    代價講明：真沉默的偵測最多延後一個週期，且只在 1～2 倍門檻的區間。
    這是刻意的取捨 —— 延後一個週期，換掉每次 rebuild 都出現的假紅。
    """
    if age <= threshold:
        return None
    if uptime and (age - uptime) <= threshold:
        return (f"扣掉重啟後的 {uptime/3600:.1f}h 即為 "
                f"{(age-uptime)/3600:.1f}h，尚不足以判定")
    interval = threshold / 2
    if uptime and uptime < interval and age < threshold * 2:
        return (f"行程啟動僅 {uptime/3600:.1f}h＜週期 {interval/3600:.1f}h，"
                f"這次啟動後它還沒有過執行機會")
    return None


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
    # 2026-08-12：整段註解掉的 add_job 也會被比對到 —— `shadow_baseline_export`
    # 的排程 v6.12 就刻意移除了，只留註解，卻仍被推導成一個「應該存在的排程」，
    # 而它永遠不可能有訊號。幽靈閾值會讓覆蓋率的分母虛胖，也會在下面的
    # 「有閾值卻沒訊號」清單裡製造一筆永遠修不掉的雜訊。
    src = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    conditional = _conditionally_registered_ids(src)
    if conditional:
        print(f"  · 條件註冊、未必存在的排程不列入閾值：{', '.join(sorted(conditional))}")
    out: dict[str, int] = {}
    for m in _ADD_JOB_RE.finditer(src):
        secs = _interval_seconds(m.group(1), m.group("args"))
        if not secs:
            continue
        jid = m.group("jid").rstrip("_")  # f-string 前綴會留下尾端底線
        if jid in conditional:
            continue
        # 同名 job 註冊多次（多時段）→ 取最短週期，否則會低估頻率而漏抓
        out[jid] = min(out.get(jid, secs * 2), secs * 2)
    return out


def _conditionally_registered_ids(src: str) -> set[str]:
    """包在 `if ...:` 底下的 add_job —— 條件不成立時它根本不會被註冊。

    2026-08-12：`einvoice_sync` 包在 `if os.getenv("MOF_APP_ID")` 內，環境變數沒設
    就從不註冊，於是「從未有執行紀錄」是預期而非故障。把它算成應有排程，
    會在『沒有任何訊號』清單裡留下一筆永遠修不掉的雜訊 —— 而永遠亮著的燈
    等於沒有燈。判準看**直接包住它的那個區塊是不是 if**（`for hour in [...]`
    那種迴圈註冊仍然會真的註冊，不能一併排除）。
    """
    lines = src.splitlines()
    out: set[str] = set()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("scheduler.add_job("):
            continue
        indent = len(line) - len(line.lstrip())
        for j in range(i - 1, -1, -1):
            prev = lines[j]
            if not prev.strip():
                continue
            prev_indent = len(prev) - len(prev.lstrip())
            if prev_indent >= indent:
                continue
            if prev.lstrip().startswith("if "):
                m = re.search(r"id=f?['\"]([a-z0-9_]+)", "\n".join(lines[i:i + 12]))
                if m:
                    out.add(m.group(1).rstrip("_"))
            break
    return out


def _tracked_job_ids(src_path: Path | None = None) -> set[str]:
    """哪些 job 有 @tracked_job —— 只有它們會寫進 cron_events.jsonl。

    沒有這個裝飾的 job（如 kg_metrics_refresh）本來就不留持久紀錄，
    「cron_events 查無此人」對它們是預期，不是故障。少了這個區分，
    下面的「無任何訊號」清單會把設計如此的東西報成異常。
    """
    p = src_path or _scheduler_path()
    if p is None:
        return set()
    try:
        src = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()
    return set(re.findall(r"@tracked_job\(\s*['\"]([a-z0-9_]+)['\"]", src))


def _cron_events_path() -> Path | None:
    """cron_events.jsonl —— host 與容器路徑不同，兩個都試（同 _scheduler_path 的教訓）。

    ⚠️ 2026-08-12 踩到的坑，值得寫下來：本函式初版把 host 候選寫成
    `<repo>/logs/cron_events.jsonl`（錯的，compose 掛的是 `./backend/logs:/app/logs`），
    於是往下試容器路徑 `/app/logs/...`。**在 Windows 上這不會失敗** ——
    `/app` 被當成磁碟根相對路徑解析成 `D:\\app\\`，而那個目錄真的存在
    （過去某次在 host 執行帶容器路徑的程式碼時被靜靜建出來的），
    裡面躺著一份 08-10 的舊 cron_events。結果就是：讀到了、有資料、看起來很正常，
    然後據此把 36 個健康的排程判成「從未執行」、把一個正常的判成 dormant。
    在 Linux 上路徑寫錯會 FileNotFoundError，在 Windows 上會**讀到一份假的**。
    → 容器候選只在非 Windows 採用；host 一律走 compose 掛載的真實位置。
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "backend" / "logs" / "cron_events.jsonl",  # host（compose 掛載來源）
    ]
    if os.name != "nt":
        candidates.append(Path("/app/logs/cron_events.jsonl"))       # container
    for p in candidates:
        if p.exists():
            return p
    return None


def fetch_last_event_ages() -> dict[str, float] | None:
    """從持久的 cron_events.jsonl 取每個 job 最後一次執行距今幾秒。

    為什麼需要第二個來源：/metrics 的 gauge 是**行程內**的，容器一重啟就從零開始，
    只有「重啟後跑過」的 job 才有值。2026-08-12 凌晨異常關機（02:52 斷、05:43 恢復），
    當時 55 個推導出閾值的排程裡只有 15 個出現在 /metrics —— 其餘 40 個不是健康、
    不是異常，而是**根本不在畫面上**，本支照樣印「✓ all monitored cron」。
    「不在監控範圍」與「監控通過」不得長得一樣。
    cron_events.jsonl 是落地檔案、跨重啟存活，正好補上這個缺口。
    """
    p = _cron_events_path()
    if p is None:
        return None
    now = datetime.now()
    last: dict[str, datetime] = {}
    try:
        with p.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    e = json.loads(line)
                    ts = datetime.fromisoformat(e["ts"])
                except Exception:
                    continue
                jid = e.get("job_id")
                if jid and (jid not in last or ts > last[jid]):
                    last[jid] = ts
    except Exception as e:
        print(f"ERR: cron_events 讀取失敗：{e}")
        return None
    if not last:
        print(f"ERR: {p} 沒有任何可解析的事件")
        return None
    # 新鮮度守衛：backend 有在跑（我們拿得到 /metrics）卻讀到一份幾天前就停止
    # 增長的紀錄檔，那就不是權威來源，而是某個副本。用它判定會得出精確而錯誤的
    # 結論 —— 上面 docstring 記的 D:\app 事件正是如此。寧可說「沒有依據」。
    newest_age_h = min((now - t).total_seconds() for t in last.values()) / 3600
    if newest_age_h > 6:
        print(f"ERR: {p} 最新事件已 {newest_age_h:.0f}h 前 —— 疑為過期副本，不採信")
        return None
    return {j: (now - t).total_seconds() for j, t in last.items()}


def fetch_process_uptime() -> float | None:
    """backend 行程已經跑了多久（秒）。

    2026-08-13：同一天內兩次因為我自己 rebuild 而產生假 RED ——
    `process_reminders` / `health_check_broadcast` 是 5 分鐘級 job（門檻 12 分鐘），
    而 rebuild + 重啟的空窗約 14 分鐘，於是重啟後前十幾分鐘必然被判 dormant。

    等它自己好不算修：每次後端 rebuild 都產生一次假紅，而假紅正是本專案
    明文定義的告警疲勞（「連三天推同一則等於訓練人略過它」）。
    行程剛啟動時，週期短於「已啟動時間」的 job 本來就不可能已經 fire 過。
    """
    try:
        with urllib.request.urlopen("http://localhost:8001/metrics", timeout=10) as r:
            text = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    for line in text.splitlines():
        if line.startswith("process_start_time_seconds "):
            try:
                return datetime.now().timestamp() - float(line.rsplit(" ", 1)[1])
            except ValueError:
                return None
    return None


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

    # 重啟會重置 IntervalTrigger：下一次 fire 是「重啟時刻 + 週期」，
    # 所以重啟後那段時間的沉默是必然的，不是故障。
    #
    # ⚠️ 但重啟**只解釋得了重啟之後那一段**。原本寫成「uptime < 1 小時才豁免」
    # 是個武斷的切點：2026-08-15 一次 rebuild 之後 uptime 2 小時、
    # `llm_quota_check`（6 小時週期 / 12 小時門檻）就被判成 dormant ——
    # 而它只是還沒輪到。反過來，若某個 job 其實已經沉默 200 小時，
    # 剛重啟也不該讓它變綠。
    #
    # 正解是**把重啟後的時間從 age 裡扣掉**再跟門檻比：
    #   dormant ⇔ (age − uptime) > threshold
    # 這同時滿足兩邊 —— 剛重啟不會製造假紅，真沉默也蓋不住。
    # 取不到 uptime 時 discount = 0（不豁免），保守。
    uptime = fetch_process_uptime()
    discount = uptime or 0.0
    if discount:
        would_red = {j for j, t in thresholds.items()
                     if ages.get(j, 0) > t and ages.get(j, 0) - discount <= t}
        if would_red:
            print(f"  · backend 行程已啟動 {discount/3600:.1f}h —— 判定時扣除這段"
                  f"（重啟重置 IntervalTrigger）；{len(would_red)} 個 job 因此不判 dormant")

    for jid, age in sorted(ages.items()):
        threshold = thresholds.get(jid)
        if threshold is None:
            unknown_jobs.append(jid)
            print(f"  ⚪ {jid:38} age={age/3600:.1f}h (no threshold)")
            continue
        ratio = age / threshold
        _why = cannot_judge(age, threshold, discount)
        if _why:
            healthy += 1
            print(f"  ⏳ {jid:38} age={age/3600:.1f}h > max {threshold/3600:.1f}h —— {_why}")
        elif age > threshold:
            red_jobs.append(jid)
            print(f"  🔴 {jid:38} age={age/3600:.1f}h > max {threshold/3600:.1f}h ({ratio:.1f}x)")
        elif age > threshold * 0.5:
            print(f"  🟡 {jid:38} age={age/3600:.1f}h / max {threshold/3600:.1f}h ({ratio:.0%})")
            healthy += 1
        else:
            print(f"  🟢 {jid:38} age={age/3600:.1f}h / max {threshold/3600:.1f}h ({ratio:.0%})")
            healthy += 1

    # ------------------------------------------------------------------
    # 有閾值卻沒有指標的 job —— 2026-08-12 新增。
    #
    # 上面那個迴圈只走訪 /metrics 給的東西，於是「該被監控卻沒出現在指標裡」
    # 的排程連一行都不會被印出來。當日 55 個閾值只有 15 個有指標，
    # 而畫面顯示 15/15 全綠。這正是它要抓的那種沉默，只是發生在它自己身上。
    # ------------------------------------------------------------------
    event_ages = fetch_last_event_ages()
    tracked = _tracked_job_ids()
    missing = sorted(set(thresholds) - set(ages))
    blind: list[str] = []          # 兩個來源都查不到＝完全沒有訊號
    if missing:
        print()
        print(f"— {len(missing)} 個排程有閾值但 /metrics 沒有指標（行程重啟後尚未跑過），"
              f"改以 cron_events 持久紀錄判定：")
        if event_ages is None:
            # 找不到持久紀錄就等於這 40 個完全沒人看 —— 必須出聲，不得靜默略過
            print("  ✗ 找不到 cron_events.jsonl —— 這些排程本次無任何判定依據")
            blind = list(missing)
        else:
            for jid in missing:
                threshold = thresholds[jid]
                age = event_ages.get(jid)
                if age is None:
                    if jid not in tracked:
                        # 沒有 @tracked_job 就不會寫 cron_events，這是設計而非故障，
                        # 但它同時也沒有 gauge → 誠實說出「這支沒有任何存活訊號」。
                        # 收束方式已知：下次 backend rebuild 時替它們補上 @tracked_job，
                        # 就跟其餘 53 支一樣有持久紀錄。刻意不為兩個裝飾子單獨 rebuild
                        # （backend/app 非 bind mount），所以它會黃到那時為止。
                        print(f"  ⚪ {jid:38} 無 @tracked_job，不留持久紀錄＝無存活訊號")
                    else:
                        print(f"  ⚪ {jid:38} 從未有執行紀錄（可能條件註冊未啟用）")
                    blind.append(jid)
                elif cannot_judge(age, threshold, discount):
                    healthy += 1
                    print(f"  ⏳ {jid:38} age={age/3600:.1f}h > max {threshold/3600:.1f}h"
                          f" —— {cannot_judge(age, threshold, discount)}（持久紀錄）")
                elif age > threshold:
                    red_jobs.append(jid)
                    print(f"  🔴 {jid:38} age={age/3600:.1f}h > max {threshold/3600:.1f}h（持久紀錄）")
                else:
                    healthy += 1
                    print(f"  🟢 {jid:38} age={age/3600:.1f}h / max {threshold/3600:.1f}h（持久紀錄）")

    print()
    print(f"Summary: {healthy} healthy / {len(red_jobs)} RED / "
          f"{len(unknown_jobs)} unknown / {len(blind)} 無訊號")

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

    # (d) 2026-08-12：兩個來源都查不到的排程不算通過。它們沒有失敗、沒有紀錄、
    #     也不在任何一行綠字裡 —— 正是本支存在要抓的那種安靜。
    if blind:
        print(f"🟡 {len(blind)} 個排程沒有任何存活訊號（既無指標也無執行紀錄）：")
        for j in blind:
            print(f"    - {j}")
        print("   → 不是「監控通過」，是「沒有人看得見它」")
        return 1

    print(f"✓ {healthy} 個排程皆在門檻內（指標 {len(ages)} + 持久紀錄 "
          f"{max(0, healthy - len(ages))}），無盲區")
    return 0


if __name__ == "__main__":
    sys.exit(main())
