# -*- coding: utf-8 -*-
"""呼叫 pm2 之前的護欄 —— 因為 pm2 CLI 連不上 daemon 時會 spawn 一個不會退出的。

2026-09-02（由 `ck-aaap-58` 跨 session 通報後在本 repo 實證）：

重開機後 `pm2 jlist` 一律回 `connect EPERM //./pipe/rpc.sock`，
而 **pm2 CLI 每次連不上就 spawn 一個惰性 daemon（約 50 MB，不會自己退出）**。
本機實測 12:xx：**98 個行程、5,125 MB**。

⚠️ 最該記住的一點：本 repo 的兩支 pm2 稽核**修正確性沒有修掉副作用** ——
`pm2_declared_vs_running_audit` 的 candidates 迴圈一輪最多呼叫 5 次，
而我當天為了驗證另一個修法跑了它兩次。**檢核本身是洩漏源。**

⇒ 判準：**呼叫一個「失敗時會產生副作用」的外部工具之前，先問它現在健不健康。**
   不健康就 SKIP-LOUD（大聲跳過），不要「試試看說不定這次會成功」——
   那個「試試看」每次都要付代價。

清理既有的惰性 daemon **不在本模組職責內**（那是有副作用的動作，屬 owner；
且重開機會自然清掉）。本模組只負責「不要再製造」。
"""
from __future__ import annotations

import subprocess

# 門檻：正常情況下 pm2 daemon 應該只有 1 個（God Daemon）。
#
# 2026-09-02（第三版）：**原本給到 3「容忍暫態」，那是一個漏三次的授權。**
# 實測：daemon 被清空後我連續跑檢核，護欄在 <=3 時每次都放行，
# 於是 0 → 5 —— **每一次放行都製造了一個，直到超過門檻才擋下**。
# 門檻不是「容忍度」，是「在它擋下之前允許洩漏幾次」。
#
# 改成 1：只容忍真正的 God Daemon。代價是 pm2 正常時若剛好有第二個
# 短暫存在會誤擋一次（YELLOW，不是 RED），那個代價遠低於持續洩漏。
DEFAULT_THRESHOLD = 1

# 2026-09-02（同日第二版）：**第一版有假零。**
#
# 原本只回「CommandLine 含 pm2/God 的 node 行程數」。實測踩到：
# node.exe 有 5 個，而其中 4 個**讀不到 CommandLine**（回 null，權限或跨 session）
# ⇒ 過濾條件全部為 False ⇒ 回 0 ⇒ 護欄判定「安全」⇒ 照常呼叫 pm2。
#
# **護欄失效的方向是放行** —— 而它失效的時機正好是環境異常的時候。
# docstring 原本寫著「數不出來回 None，不假裝是 0」，但實作把
# 「讀不到 CommandLine」算成了「不符合條件」而不是「數不出來」。
# ⇒ **寫下的判準與實作之間，還隔著一次「這個查詢在拿不到資料時會回什麼」。**
#
# 改成同時取三個數，讓呼叫端能分辨「真的是 0」與「我看不到」。
_PS_COUNT = (
    "$all = @(Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" -ErrorAction SilentlyContinue); "
    "$known = @($all | Where-Object { $_.CommandLine }); "
    "$hit = @($known | Where-Object { $_.CommandLine -like '*God*' -or $_.CommandLine -like '*pm2*' }); "
    "\"$($all.Count) $($known.Count) $($hit.Count)\""
)


def pm2_daemon_count() -> int | None:
    """目前有幾個 pm2 相關的 node 行程。**數不出來回 None，不回 0。**

    回 None 的兩種情況：
    · PowerShell 本身失敗
    · **有 node 行程存在，但一個都讀不到 CommandLine** —— 此時「符合條件 0 個」
      是「我看不到」不是「沒有」（L133 的形狀，同日第二次踩到）
    """
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _PS_COUNT],
            capture_output=True, timeout=20, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            return None
        parts = (r.stdout or "").strip().splitlines()[-1].split()
        if len(parts) != 3:
            return None
        total, known, hit = (int(x) for x in parts)
        if total > 0 and known == 0:
            # 有 node 行程但全部讀不到 CommandLine ⇒ 不可信
            return None
        return hit
    except Exception:
        return None


def pm2_safe_to_call(threshold: int = DEFAULT_THRESHOLD) -> tuple[bool, str]:
    """呼叫 pm2 之前問這個。

    回 `(safe, reason)`。`safe=False` 時**不要呼叫 pm2** —— 每呼叫一次
    就多一個約 50 MB 且不會退出的 daemon。

    數不出來時回 `True` 並在 reason 說明：**護欄失效的方向要選在
    「不擋住正常運作」那一側**，但要留得下痕跡（同 L133「我看不到」不等於「有問題」）。
    """
    n = pm2_daemon_count()
    if n is None:
        # ⚠️ 這一支的取捨方向與別處不同，理由要寫下來：
        # 這裡回 True（照常呼叫）是因為「擋住正常運作」的代價高於「多一個 daemon」。
        # 但它確實是一個已知的放行缺口 —— 若日後洩漏在護欄上線後仍繼續，
        # **先來看是不是每次都走進了這一條**。
        return True, "無法可信地計數 pm2 行程（護欄未生效，仍照常呼叫）"
    if n > threshold:
        return False, (
            f"偵測到 {n} 個 pm2 相關行程（門檻 {threshold}）—— "
            f"pipe 很可能是 EPERM，每呼叫一次 pm2 就會多一個約 50 MB 的惰性 daemon。"
        )
    return True, f"pm2 行程 {n} 個，在門檻內"
