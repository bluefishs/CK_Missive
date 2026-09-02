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
# 給到 3 是容忍暫態；超過就代表 pipe 已經不通、每呼叫一次就多一個。
DEFAULT_THRESHOLD = 3

_PS_COUNT = (
    "(Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" -ErrorAction SilentlyContinue "
    "| Where-Object { $_.CommandLine -like '*God*' -or $_.CommandLine -like '*pm2*' } "
    "| Measure-Object).Count"
)


def pm2_daemon_count() -> int | None:
    """目前有幾個 pm2 相關的 node 行程。數不出來回 None（**不假裝是 0**）。"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _PS_COUNT],
            capture_output=True, timeout=20, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            return None
        return int((r.stdout or "").strip().splitlines()[-1])
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
        return True, "無法計數 pm2 行程（護欄未生效，仍照常呼叫）"
    if n > threshold:
        return False, (
            f"偵測到 {n} 個 pm2 相關行程（門檻 {threshold}）—— "
            f"pipe 很可能是 EPERM，每呼叫一次 pm2 就會多一個約 50 MB 的惰性 daemon。"
        )
    return True, f"pm2 行程 {n} 個，在門檻內"
