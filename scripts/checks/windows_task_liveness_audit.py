# -*- coding: utf-8 -*-
"""Windows 排程存活稽核（2026-08-05）。

## 為什麼需要這一支

「排程註冊了」不等於「排程會跑」—— 這件事在 08-01/08-02 一天內踩了三次
（celery beat 未重啟／task 未 import／schtasks 預設不補跑），而且**手動呼叫都會過**，
唯一驗法是看執行端真的有沒有動。既有的 `scheduler_liveness_audit.py` 管的是
容器內 APScheduler，**跑在 host 上的 15 支 Windows 排程沒有任何人在看**：
自我走查（Missive/lvrland/CK_Website）、能力使用度快照、異地備份、Hermes tick
全都靠它們，任一支悄悄停掉，畫面上不會有任何變化。

刻意**不另建一份排程清單**（那就是這個專案一直在治的異質同工）——
直接問作業系統有哪些 `CK` 開頭的排程，新增排程自動納入，不需要有人記得來登記。

## 判準

  State          必須 Ready/Running（Disabled＝有人關掉了而沒人知道）
  LastTaskResult 必須 0，或在 ALLOWED_NONZERO 裡**寫明理由**
  StartWhenAvailable 必須為真 —— 否則機器關機那次就整個跳過且無訊號（08-02 教訓）
  LastRunTime    逾 MAX_AGE_DAYS 未跑＝可能已停擺（登入觸發型無法用時間判，故排除）

執行：
    python scripts/checks/windows_task_liveness_audit.py
    python scripts/checks/windows_task_liveness_audit.py --strict   # 有 RED → exit 1

退出碼：0 GREEN / 1 RED（--strict）/ 2 未驗完（查不到排程，不得當成正常）
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 納管哪些排程 —— 2026-08-11 由 `^CK[-_]` 放寬。
#
# 原本只認 CK 前綴，看起來合理（我們的東西都叫 CK_*），但它有個盲區：
# **命名不合規的排程等於不存在**。實例：CK_lvrland_Webmap 的備份排程叫
# `LandValuation_Daily_Backup`（由該 repo 的 Setup-AutoBackup.ps1 註冊），
# 不符前綴 → 就算真的註冊了，這支稽核也永遠看不到它；
# 而實際情況更糟 —— 它根本沒被註冊過，而異地備份因此停了 154 天沒有人知道。
#
# 用「白名單前綴 + 已知的專案關鍵字」而不是掃全部：Windows 內建排程有數百個，
# 全掃會產出一份沒有人讀得完的清單，而讀不完的清單與沒有清單是同一件事。
TASK_PREFIX_RE = r"^(CK[-_]|LandValuation|StorageTank|SaltWarehouse|Hermes)"

# 走查類任務的退出碼語意：0 全過 / 1 有失敗 / 2 有跳過。
# 1 與 2 都代表**任務本身跑完了**，紅的是內容 —— 那由下面的 check_sweep_results()
# 直接讀結果 JSON 判定，不靠退出碼。把兩件事混在一起判，會變成
# 「任務掛了」與「頁面壞了」共用一個燈號，而它們的處置完全不同。
SELFAUDIT_TASK_RE = r"^(CK[_-][A-Za-z0-9_]+)-SelfAudit-(Flow|Sweep)$"

# 其餘任務的非 0 退出碼 —— **必須寫理由**，否則就是「紅燈看久了就習慣」的起點
ALLOWED_NONZERO: dict[str, dict[int, str]] = {
    # 2026-08-09：weekly fitness runner 的三態約定是 0=GREEN / **1=有 RED step** / 2+=執行失敗。
    #
    # 不宣告它會形成一個**自我循環**：本稽核把 1 判成「未宣告的失敗碼」→ 自己變成
    # weekly 的一個 RED step → weekly 因此退出 1 → 下次本稽核又判它異常。
    # 於是 weekly 永遠不可能綠，而「永遠是紅的」與「連 9 週 RED 無人知」是同一個下場：
    # 訊號失去意義。（那次 9 週 RED 正是這支稽核要防的事。）
    #
    # 只宣告 1，**刻意不宣告 2** —— 2 代表 runner 自己執行失敗（argparse 錯、腳本不存在），
    # 那是真的要出聲的。宣告的是「跑完了、紅的是內容」，內容另有接收者（digest／LINE）。
    "CK_Missive-Fitness-Weekly": {
        1: "有 RED step＝任務跑完了、紅的是內容；內容由 weekly 自己推 digest",
    },
    # 2026-08-09：靜態檢核 runner 走 portfolio 三態（0=GREEN／1=YELLOW／2+=RED）。
    # 1 代表「跑完了、有警示」——任務本身正常，內容另由下方的結果檔檢核判。
    # 同樣**刻意不宣告 2**：那是真的有 RED step，該出聲。
    "CK_PileMgmt-StaticChecks": {
        1: "有 YELLOW 警示＝任務跑完了；內容看 docs/health/static-checks.json",
    },
    "CK_lvrland_Webmap-StaticChecks": {
        1: "有 YELLOW 警示＝任務跑完了；內容看 docs/health/static-checks.json",
    },
}

# 逾期門檻：日排程與週排程共用一個保守值 —— 只用來抓「整支停擺」。
# 刻意不做「每支排程各自的預期頻率」表 —— 那會變成第二份排程清單，
# 而排程的真實頻率就寫在作業系統的 trigger 裡，兩份必然漂移。
MAX_AGE_DAYS = 8

# 「錯過未補跑」的緩衝。2026-08-12 立案，見 audit() 內說明。
# 給 2 小時是因為排程本身可能延遲觸發、或正在執行中還沒更新 LastRunTime。
MISSED_GRACE_HOURS = 2


def _interval_days(task: dict) -> int:
    """該排程的週期天數（日／週觸發）；純登入或開機觸發回 0。

    PowerShell 5.1 的 ConvertTo-Json 對「管線只剩一個元素」仍可能序列化成陣列
    （同檔頭已記過 -AsArray 不存在那個坑）→ Python 端再正規化一次，不與它角力。
    """
    v = task.get("IntervalDays") or 0
    if isinstance(v, list):
        v = v[0] if v else 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def query_tasks() -> list[dict]:
    """問作業系統要 CK 開頭的排程。查不到就是查不到，不編造空清單。"""
    # 注意：Windows PowerShell 5.1 的 ConvertTo-Json **沒有 -AsArray**，
    # 且單一元素會被序列化成物件而非陣列 → 用 @() 強制成陣列，Python 端也再防一次。
    ps = (
        "$ErrorActionPreference='Stop';"
        "@(Get-ScheduledTask | Where-Object { $_.TaskName -match '" + TASK_PREFIX_RE + "' } |"
        " ForEach-Object { $i = $_ | Get-ScheduledTaskInfo;"
        "   [PSCustomObject]@{"
        "     Name=$_.TaskName; State=[string]$_.State;"
        "     Result=$i.LastTaskResult;"
        "     LastRun=(if($i.LastRunTime){$i.LastRunTime.ToString('s')}else{''});"
        "     NextRun=(if($i.NextRunTime){$i.NextRunTime.ToString('s')}else{''});"
        "     IntervalDays=(@($_.Triggers | ForEach-Object {"
        "        if ($_.CimClass.CimClassName -match 'Daily') { [int]$_.DaysInterval }"
        "        elseif ($_.CimClass.CimClassName -match 'Weekly') { 7 * [int]$_.WeeksInterval }"
        "        else { 0 } } | Where-Object { $_ -gt 0 } | Sort-Object | Select-Object -First 1));"
        "     StartWhenAvailable=[bool]$_.Settings.StartWhenAvailable;"
        "     LogonTrigger=[bool](@($_.Triggers | Where-Object { $_.CimClass.CimClassName -match 'Logon|Boot' }).Count);"
        "     TimeLimit=[string]$_.Settings.ExecutionTimeLimit"
        "   } }) | ConvertTo-Json -Depth 3"
    )
    # Windows PowerShell 5.1 沒有 if 運算式，改用 subexpression
    ps = ps.replace(
        "(if($i.LastRunTime){$i.LastRunTime.ToString('s')}else{''})",
        "$(if ($i.LastRunTime) { $i.LastRunTime.ToString('s') } else { '' })",
    )
    ps = ps.replace(
        "(if($i.NextRunTime){$i.NextRunTime.ToString('s')}else{''})",
        "$(if ($i.NextRunTime) { $i.NextRunTime.ToString('s') } else { '' })",
    )
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0 or not (out.stdout or "").strip():
        raise RuntimeError((out.stderr or "PowerShell 無輸出").strip()[:300])
    data = json.loads(out.stdout)
    return data if isinstance(data, list) else [data]


def check_sweep_results(tasks: list[dict], portfolio_root: Path) -> tuple[list[str], list[str]]:
    """讀各 repo 走查結果 JSON 的**內容** —— 「跑了」與「結果是好的」是兩件事。

    2026-08-05 立案：pile 導入當天，排程 LastTaskResult=1（有失敗）而任務本身完全正常。
    若只看退出碼，得到的是「任務壞了」的誤判；若只看任務狀態，則 3 個真實故障頁面
    完全沒有人看得到。CK_Missive 自己的結果已由 producer registry 的 json_result
    納管，但 lvrland / CK_Website / pile 的結果**沒有任何人在讀** ——
    刻意在同一支稽核裡處理，而不是為此再開一份跨 repo 清單。
    """
    reds: list[str] = []
    notes: list[str] = []
    for t in tasks:
        m = re.match(SELFAUDIT_TASK_RE, t.get("Name", ""))
        if not m:
            continue
        repo, kind = m.group(1), m.group(2).lower()
        # 結果檔位置**讀各 repo 自己的 selfaudit.config.json**，不在這裡寫死。
        # 初版寫死 docs/health/ 立刻誤報 CK_Missive「結果檔不存在」——
        # 它的輸出在 wiki/memory/integration-health/。把路徑複製一份到這裡，
        # 就是又造一份會漂移的事實，而本檔正是為了消滅那種東西。
        cfg_path = portfolio_root / repo / "selfaudit.config.json"
        if not cfg_path.exists():
            reds.append(f"{repo}: 有走查排程卻沒有 selfaudit.config.json")
            continue
        try:
            out = json.loads(cfg_path.read_text(encoding="utf-8"))["output"]
            rel = out["flow_result" if kind == "flow" else "sweep_result"]
        except Exception as e:
            reds.append(f"{repo}: selfaudit.config.json 讀不到 output 路徑（{e}）")
            continue
        f = portfolio_root / repo / rel
        if not f.exists():
            reds.append(f"{repo} {kind}: 結果檔不存在（{f.name}）—— 排程跑了卻沒有產出")
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            reds.append(f"{repo} {kind}: 結果檔無法解析（{e}）")
            continue
        n_pass, n_fail = int(d.get("pass") or 0), int(d.get("fail") or 0)
        # pass=0 且 fail=0 ＝ 什麼都沒掃到；設定寫錯與大面積失效長得一樣，不可判綠
        if n_pass == 0 and n_fail == 0:
            reds.append(f"{repo} {kind}: 掃到 0 項（0 項不等於全部健康）")
        elif n_fail > 0:
            reds.append(f"{repo} {kind}: fail={n_fail}（頁面層有真實故障，看 {f}）")
        else:
            notes.append(f"{repo} {kind}: pass={n_pass} fail=0")
    return reds, notes


# Windows 排程器的 `SCHED_S_*` 狀態碼（0x000413xx）—— **不是任務的結束碼**。
# 把它們當失敗會製造週期性假告警：高頻排程被抽查到「正在執行中」是常態。
# 刻意只列狀態碼，不含任何真正的錯誤碼（0x8004xxxx 那些仍該紅）。
SCHED_STATUS_CODES: dict[int, str] = {
    0x00041300: "SCHED_S_TASK_READY（就緒，尚未到觸發時間）",
    0x00041301: "SCHED_S_TASK_RUNNING（正在執行中）",
    0x00041303: "SCHED_S_TASK_HAS_NOT_RUN（註冊後尚未執行過）",
    0x00041304: "SCHED_S_TASK_NO_MORE_RUNS（沒有後續排程）",
    # 刻意**不列** 0x00041306 SCHED_S_TASK_TERMINATED：任務被逾時或人工中止
    # 是該出聲的事（多半代表 ExecutionTimeLimit 設太短或卡住），讓它照常判紅。
}

BACKUP_TASK_RE = r"^(CK[_-][A-Za-z0-9_]+)-MinIO-Offsite$"
BACKUP_STATUS_REL = "backups/minio-offsite-status.json"
BACKUP_STALE_HOURS = 36  # 每日排程 + 一次容錯


def check_backup_results(tasks: list[dict], portfolio_root: Path) -> tuple[list[str], list[str]]:
    """讀異地備份的**狀態檔內容** —— 排程「跑完了」不等於「東西真的在 NAS 上」。

    2026-08-09 立案。DT 的 MinIO 原本完全沒有備份，而 `scripts/backup.sh` 是把
    DB dump **上傳到 MinIO** —— MinIO 是備份的目的地不是來源，於是資料與其備份
    在同一顆磁碟上。補上異地備份後，若只看排程退出碼，會重演 2026-07-30 Missive
    那次「異地備份看起來沒在跑」：腳本回 0、實際 NAS 上什麼都沒有。

    故這裡讀的是腳本寫回的 **NAS 實況**（份數/大小），不是「腳本說自己成功了」。
    狀態檔位置由任務名推導（同走查的作法），不另建一份跨 repo 清單。
    """
    reds: list[str] = []
    notes: list[str] = []
    for t in tasks:
        m = re.match(BACKUP_TASK_RE, t.get("Name", ""))
        if not m:
            continue
        repo = m.group(1)
        f = portfolio_root / repo / BACKUP_STATUS_REL
        if not f.exists():
            reds.append(f"{repo}: 有異地備份排程卻沒有狀態檔（{BACKUP_STATUS_REL}）")
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            reds.append(f"{repo}: 備份狀態檔無法解析（{e}）")
            continue
        if d.get("result") != "ok":
            reds.append(f"{repo}: 異地備份 result={d.get('result')}（{str(d.get('detail'))[:80]}）")
            continue
        # 「成功但 0 檔」必須是紅的 —— 那是最像成功的失敗
        n = int(d.get("nas_files") or 0)
        if n <= 0:
            reds.append(f"{repo}: 異地備份回報 ok 但 NAS 上 0 檔")
            continue
        ts = str(d.get("finished_at") or "")
        try:
            age_h = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
        except ValueError:
            reds.append(f"{repo}: 備份狀態檔時間無法解析（{ts}）")
            continue
        if age_h > BACKUP_STALE_HOURS:
            reds.append(f"{repo}: 異地備份已 {age_h:.0f} 小時未更新（門檻 {BACKUP_STALE_HOURS}h）")
        else:
            notes.append(f"{repo} 異地備份: NAS {n} 檔 / {d.get('nas_size_mb')} MB（{age_h:.0f}h 前）")
    return reds, notes


STATIC_TASK_RE = r"^(CK[_-][A-Za-z0-9_]+)-StaticChecks$"
STATIC_RESULT_REL = "docs/health/static-checks.json"

# 走查排程的**前置檢核**結果 —— 與走查本身分開判。
#
# 2026-08-09 實測缺口：DT 的走查排程把資產完整性當前置跑，前置 RED 會讓
# 排程退出 1；但 SelfAudit 任務的 1/2 被豁免為「跑完了、內容另判」，
# 而「內容」只讀走查 JSON（fail=0）→ **排程稽核顯示 DT 全 GREEN，
# 而資產稽核正在報 7 筆 crack 無產物、tiles 全空**。
# 前置的產出必須有自己的接收者，否則就是「跑了但沒人看」。
PRECHECK_RESULTS: dict[str, list[tuple[str, str]]] = {
    "CK_DigitalTunnel": [("資產完整性", "docs/health/asset-integrity.json")],
}
STATIC_STALE_HOURS = 36  # 每日排程 + 一次容錯


def check_static_results(tasks: list[dict], portfolio_root: Path) -> tuple[list[str], list[str]]:
    """讀各 repo 靜態檢核的**結果內容** —— 「排程跑完了」不等於「檢核是綠的」。

    2026-08-09 立案：在此之前，靜態層（第 1 階）實質**只在 CK_Missive 存在** ——
    lvrland 有 runner 但無排程（celery 只監看產出新鮮度、沒有生產端，
    它當天顯示新鮮只因為有人手動跑過）、pile 的 6 支檢核完全沒有東西會跑。
    補上排程後若只看退出碼，會重演「跑了但沒人看結果」。
    """
    reds: list[str] = []
    notes: list[str] = []
    for t in tasks:
        m = re.match(STATIC_TASK_RE, t.get("Name", ""))
        if not m:
            continue
        repo = m.group(1)
        f = portfolio_root / repo / STATIC_RESULT_REL
        if not f.exists():
            reds.append(f"{repo}: 有靜態檢核排程卻沒有結果檔（{STATIC_RESULT_REL}）")
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            reds.append(f"{repo}: 靜態檢核結果檔無法解析（{e}）")
            continue
        steps = int(d.get("steps") or 0)
        # 「跑了 0 步」與「全部通過」在 state 上都可能是 GREEN —— 必須分開
        if steps <= 0:
            reds.append(f"{repo}: 靜態檢核跑了 0 步（0 步不等於全部健康）")
            continue
        state = str(d.get("state") or "")
        ts = str(d.get("checked_at") or "").replace("Z", "")
        try:
            age_h = (datetime.utcnow() - datetime.fromisoformat(ts)).total_seconds() / 3600
        except ValueError:
            reds.append(f"{repo}: 靜態檢核時間無法解析（{ts}）")
            continue
        if age_h > STATIC_STALE_HOURS:
            reds.append(f"{repo}: 靜態檢核已 {age_h:.0f} 小時未更新（門檻 {STATIC_STALE_HOURS}h）")
        elif state == "RED":
            reds.append(f"{repo}: 靜態檢核 RED（fail={d.get('fail')}，看 {f}）")
        else:
            notes.append(f"{repo} 靜態檢核: {state} {steps} 步（{age_h:.0f}h 前）")
    return reds, notes


def check_precheck_results(portfolio_root: Path) -> tuple[list[str], list[str]]:
    """讀走查排程的前置檢核結果 —— 它們的 RED 會被排程退出碼的豁免吃掉。"""
    reds: list[str] = []
    notes: list[str] = []
    for repo, items in PRECHECK_RESULTS.items():
        for label, rel in items:
            f = portfolio_root / repo / rel
            if not f.exists():
                reds.append(f"{repo} {label}: 結果檔不存在（{rel}）—— 前置沒跑或沒落地")
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8-sig"))
            except Exception as e:  # noqa: BLE001
                reds.append(f"{repo} {label}: 結果檔無法解析（{e}）")
                continue
            ts = str(d.get("checked_at") or "").replace("Z", "")
            try:
                age_h = (datetime.utcnow() - datetime.fromisoformat(ts)).total_seconds() / 3600
            except ValueError:
                reds.append(f"{repo} {label}: 時間無法解析（{ts}）")
                continue
            if age_h > STATIC_STALE_HOURS:
                reds.append(f"{repo} {label}: 已 {age_h:.0f} 小時未更新（門檻 {STATIC_STALE_HOURS}h）")
            elif str(d.get("state")) == "RED":
                reds.append(f"{repo} {label}: RED（看 {f}）")
            else:
                notes.append(f"{repo} {label}: {d.get('state')}（{age_h:.0f}h 前）")
    return reds, notes


def audit(tasks: list[dict]) -> tuple[list[str], list[str]]:
    reds: list[str] = []
    notes: list[str] = []
    now = datetime.now()

    for t in tasks:
        name = t.get("Name", "?")
        state = (t.get("State") or "").strip()
        result = t.get("Result")
        last_run = (t.get("LastRun") or "").strip()
        swa = bool(t.get("StartWhenAvailable"))
        logon = bool(t.get("LogonTrigger"))

        if state not in ("Ready", "Running"):
            reds.append(f"{name}: State={state}（非 Ready＝已被停用或損壞）")

        # ExecutionTimeLimit —— 2026-08-23 新增。
        #
        # 為什麼補這個欄位：pile 的異地備份是 **PT72H**（3 天）＝形同沒有上限，
        # 而他們前一天才剛經歷「單 worker 被單一請求卡住 23 小時」。同型換到
        # 備份上，代價是那三天完全沒有異地備份而**沒有任何訊號**。
        # CK_AaaP 把這條套回自己身上，發現 `CK_AaaP_DailyCheckpoint` 也是 PT72H
        # 而實測只跑 12 秒（上限是它的 21,600 倍）；我自己也有兩支
        # （CK_Website 走查，我建的）—— 三個 repo 各有一份，沒有人在看。
        #
        # 它為什麼一直在雷達外（CK_AaaP 的診斷，值得照抄）：
        # 文件裡有「這支排程可回溯版控」的**散文**，而**散文不帶設定** ——
        # 光是「有文件寫到」不夠，要有能把它重建出來的東西，或有人在讀那個欄位。
        #
        # 判 YELLOW 不判 RED：合理的上限值因任務而異（備份要久、探針要短），
        # 我沒有一份權威表，也不打算另建第二份事實。只把**離譜的**點出來。
        tl = (t.get("TimeLimit") or "").strip()
        if tl in ("PT72H", "P3D") or tl.startswith("P") and tl.endswith("D"):
            notes.append(
                f"{name}: ExecutionTimeLimit={tl}（形同沒有上限 —— "
                f"它 hang 住時，這段時間內不會有任何訊號）")

        selfaudit = re.match(SELFAUDIT_TASK_RE, name)
        # 2026-08-09：Windows 排程的 LastTaskResult **不是只有結束碼** ——
        # 0x000413xx 是排程器自己的狀態碼，不是任務的失敗。
        # 實例：`CK-Hermes-Cron-Tick` 每 5 分鐘跑一次，抽查時剛好在執行中
        # → 267009，被判「未宣告的失敗碼」＝週期性假告警。
        if result in SCHED_STATUS_CODES:
            notes.append(f"{name}: {SCHED_STATUS_CODES[result]}（排程器狀態碼，非失敗）")
        elif result not in (0, None):
            if selfaudit and result in (1, 2):
                notes.append(
                    f"{name}: LastTaskResult={result}"
                    f"（{'有失敗' if result == 1 else '有跳過'}＝任務跑完了，內容另判）")
            else:
                reason = ALLOWED_NONZERO.get(name, {}).get(result)
                if reason:
                    notes.append(f"{name}: LastTaskResult={result} — 已知可接受（{reason}）")
                else:
                    reds.append(f"{name}: LastTaskResult={result}（未宣告的失敗碼）")

        if not swa:
            # 08-02 實際踩過：沒有這個設定，機器關機那次就整個跳過且毫無訊號。
            # ⚠️ 2026-08-12 更正：設成 True **不保證真的會補跑**。當日凌晨異常關機
            # （02:52 斷、05:43 才恢復），下列排程全部 StartWhenAvailable=True，
            # 到當日 10:30 仍一次都沒有補跑，NextRunTime 直接跳過當天排到隔天 ——
            # 其中包含異地備份，等於那一夜的 DB dump 與金鑰只留在本機一顆磁碟上。
            # 所以這個檢查只代表「沒有把補跑的可能性關掉」，真正該問的是下面那段：
            # 上一個應執行的時點過了，它到底跑了沒有。
            reds.append(f"{name}: StartWhenAvailable=False（機器關機時會整個跳過且無訊號）")

        # 2026-08-12：豁免條件由「有登入觸發」收窄為「**只有**登入觸發」。
        # 當天為三支異地備份補了登入觸發（關機錯過後靠登入補跑），若照舊寫法，
        # 它們會因此被歸為「登入觸發型，不以時間判逾期」——
        # **最需要被盯的三支剛好因為變得更可靠而退出了監控範圍**。
        # 有週期性 trigger 就照週期判，登入觸發只是額外的補跑機會。
        periodic = bool(_interval_days(t))
        if logon and not periodic:
            notes.append(f"{name}: 登入/開機觸發，不以時間判逾期")
        elif not last_run:
            reds.append(f"{name}: 從未執行過（註冊了但沒跑過）")
        else:
            try:
                age = now - datetime.fromisoformat(last_run)
                if age > timedelta(days=MAX_AGE_DAYS):
                    reds.append(f"{name}: 上次執行 {age.days} 天前（> {MAX_AGE_DAYS} 天）")
            except ValueError:
                reds.append(f"{name}: LastRun 無法解析（{last_run}）")

        # 錯過未補跑 —— 2026-08-12 新增。
        #
        # 為什麼原本抓不到：唯一的時間判定是「上次執行超過 8 天」，而每日排程漏跑
        # 一天的 age 只有 ~48h，離門檻差得遠。當日異常關機讓 03:00–05:43 之間到期的
        # 12 支排程整批沒跑，本支照樣印 GREEN —— 包含異地備份斷了一天。
        # 8 天門檻要抓的是「整支停擺」，抓不到「這一次沒跑」，兩件事需要兩個判準。
        #
        # 判準不另建頻率表（那正是本檔一開始拒絕的第二份事實）：
        # 上一個應執行時點 = 作業系統自己給的 NextRunTime − 該排程自己的 trigger 週期。
        # LastRun 落在那之前，就是這一輪沒跑到。
        next_run = (t.get("NextRun") or "").strip()
        interval_days = _interval_days(t)
        if last_run and next_run and interval_days:
            try:
                prev_due = datetime.fromisoformat(next_run) - timedelta(days=int(interval_days))
                if (datetime.fromisoformat(last_run) < prev_due
                        and now > prev_due + timedelta(hours=MISSED_GRACE_HOURS)):
                    reds.append(
                        f"{name}: 應於 {prev_due:%m-%d %H:%M} 執行卻沒跑，也沒有補跑"
                        f"（上次 {last_run[:16].replace('T', ' ')}）")
            except ValueError:
                notes.append(f"{name}: NextRun 無法解析（{next_run}），略過錯過判定")

    return reds, notes


# 「應該存在」的關鍵排程 —— 2026-08-11 新增。
#
# 為什麼本支原本抓不到最嚴重的那件事：它問的是「已註冊的排程有沒有活著」，
# 也就是只驗 A ⊆ B，沒問 B ⊆ A 破掉會怎樣（同 CK_AaaP 08-10 立的 L46）。
# 而 CK_lvrland_Webmap 的異地備份**從來沒有被註冊過** ——
# 沒有註冊就沒有紀錄、沒有失敗、沒有任何一支檢核會提到它，
# 於是那 3.9GB 只存在 D 槽一顆磁碟上，停了 154 天無人知道。
#
# 缺席的排程症狀是一片安靜，所以必須有人明確宣告「這幾支非在不可」。
# 清單刻意只放**備份類**：短、變動低、缺了的後果不可逆。
EXPECTED_TASKS = {
    "CK-Missive-Offsite-Backup":
        "CK_Missive 異地備份（DB／附件／金鑰／里程碑四類）",
    "CK_PileMgmt_DB_Backup":
        "CK_PileMgmt 資料庫異地備份",
    "CK_DigitalTunnel-MinIO-Offsite":
        "CK_DigitalTunnel MinIO 異地備份（MinIO 本身是 DB 備份的目的地，它沒有第二份）",
    # 2026-08-12 已註冊並實際觸發驗過（Result=0，NAS 145 檔 338MB → 175 檔 4.4GB）。
    # 名稱刻意**不用** `LandValuation_Daily_Backup` —— 那是該 repo
    # `Setup-AutoBackup.ps1` 給**本機** DB 備份用的名字（跑 daily_backup_enhanced.bat），
    # 而缺的一直是**異地同步**（sync_backups_to_nas.ps1）。原本這條期望把兩件事寫成一件，
    # 用了本機備份的任務名去要求異地備份存在 —— 就算有人照著註冊，
    # 註冊到的也會是錯的那一支。改用與 portfolio 一致的命名。
    "CK_lvrland_Webmap-Offsite-Backup":
        "CK_lvrland_Webmap 異地備份（backups/ → NAS，每日 03:45）—— "
        "lvrland 是公網上線的主系統，本機 backups/ 曾是唯一副本",
}


def check_expected_tasks(tasks: list[dict]) -> tuple[list[str], list[str]]:
    """該有的排程有沒有註冊。缺席即 RED —— 沒註冊的排程不會有任何失敗紀錄。"""
    present = {t.get("Name", "") for t in tasks}
    reds, notes = [], []
    for name, why in EXPECTED_TASKS.items():
        if name in present:
            continue
        reds.append(f"{name}: 應存在的排程未註冊 —— {why}")
    if not reds:
        notes.append(f"應存在的關鍵排程 {len(EXPECTED_TASKS)} 支全部在冊")
    return reds, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--ci", action="store_true", help="等同 --strict")
    args = ap.parse_args()
    strict = args.strict or args.ci

    print("=" * 70)
    print("Windows 排程存活稽核（『註冊了』不等於『會跑』）")
    print("=" * 70)

    try:
        tasks = query_tasks()
    except Exception as e:
        print(f"✗ 未驗完：無法查詢 Windows 排程 — {e}")
        print("（查不到一律 exit 2，不會因為沒看到問題就印綠燈）")
        return 2

    if not tasks:
        print("✗ 未驗完：0 支符合的排程 —— 15 支 CK 排程不可能全部消失，")
        print("  比較可能是查詢條件壞了。0 項不等於全部健康。")
        return 2

    reds, notes = audit(tasks)
    # 缺席層：該有的排程有沒有註冊（沒註冊就不會有任何失敗紀錄）
    e_reds, e_notes = check_expected_tasks(tasks)
    reds += e_reds
    notes += e_notes

    # 內容層：排程跑完了不代表結果是好的
    c_reds, c_notes = check_sweep_results(tasks, Path(__file__).resolve().parents[3])
    reds += c_reds
    notes += c_notes

    b_reds, b_notes = check_backup_results(tasks, Path(__file__).resolve().parents[3])
    reds += b_reds
    notes += b_notes

    s_reds, s_notes = check_static_results(tasks, Path(__file__).resolve().parents[3])
    reds += s_reds
    notes += s_notes

    p_reds, p_notes = check_precheck_results(Path(__file__).resolve().parents[3])
    reds += p_reds
    notes += p_notes

    for t in sorted(tasks, key=lambda x: x.get("Name", "")):
        name = t.get("Name", "?")
        bad = any(name in r for r in reds)
        print(f"  [{'RED  ' if bad else 'GREEN'}] {name:38} "
              f"result={t.get('Result')} last={(t.get('LastRun') or '從未')[:16]}")

    if notes:
        print("\n說明：")
        for n in notes:
            print(f"  · {n}")

    print("\n" + "=" * 70)
    if not reds:
        print(f"GREEN: {len(tasks)} 支 CK 排程皆存活")
        return 0
    print(f"RED: {len(reds)} 項異常")
    for r in reds:
        print(f"  - {r}")
    # 三態約定（run_fitness_*.sh）：0=GREEN / 1=YELLOW / **2+=RED**。
    # 初版非 strict 時回 0 —— 於是 weekly 裡這一步永遠是綠的，
    # 首跑抓到的 pile 3 個真實故障完全不會出現在每週結論裡。
    # 「有 RED 卻回 0」正是這支稽核自己要抓的那種假綠。
    return 2


if __name__ == "__main__":
    sys.exit(main())
