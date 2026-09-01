#!/usr/bin/env python3
"""容器重啟迴圈偵測（daily 15）

## 為什麼

2026-09-01：`ck_missive_backend` 的 `RestartCount` 從 2 漲到 14，
owner 遇到 502 —— 而**公網探針、容器 healthcheck、blackbox 全都是綠的**，
因為它是「反覆重啟後恢復」，不是持續中斷。綠燈之間的空窗才是使用者踩到的。

發現它的是**別的 repo 的 session**（CK_AaaP 從告警 sink 看到我們有 10 筆
未恢復告警、最早 13.5 小時前）。也就是說：**這件事已經叫了 13.5 小時，
而本 repo 自己的檢核一支都沒有在看。**

同一輪他們得出的結論值得抄過來：

> 偵測 → 投遞 → 消費是三層，而大家只守了前兩層。

這支補的是**本 repo 自己的第三層**：不依賴別人來告訴我們自己的容器在重啟。

## 判準（比較「上次跑的時候」與「現在」，狀態存在 `.container_restart_state.json`）

* `RestartCount` **比上次增加** → RED（正在重啟迴圈，且還在發生）
* `RestartCount` 沒增加但 **> 0 且容器啟動不到 1 小時** → YELLOW（剛重啟過，觀察中）
* 容器**被重建**（`Created` 變了 ⇒ 計數歸零）→ 不判紅，那是部署，不是故障
* 取不到 docker／容器沒在跑 → **YELLOW**（未驗 ≠ 沒問題）

⚠️ 第三條是必要的：部署會重建容器讓 `RestartCount` 歸零，
若不分辨「歸零」與「沒重啟」，這支會在每次部署後報一次假的好消息，
而在真的重啟迴圈開始時因為基準被洗掉而漏報。

## 這支不做什麼

* 不看別的 repo 的容器 —— 它們有自己的守門，跨 repo 判讀退出碼語意會誤報
  （本 repo 的 `exit 1` 是 YELLOW，別人的不一定）。
* 不嘗試修復、不重啟任何東西。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = Path(__file__).resolve().parent / ".container_restart_state.json"

#: 本 repo 自己的容器。**不看別的 repo** —— 見檔頭說明。
CONTAINERS = [
    "ck_missive_backend",
    "ck_missive_postgres",
    "ck_missive_redis",
    "ck_missive_frontend",
    "ck_missive_cloudflared",
]

#: 剛重啟過多久內仍算「觀察中」
RECENT_START_SECONDS = 3600


def _inspect(name: str) -> dict | None:
    """取容器現況；取不到回 None（呼叫端不得當成 0）。"""
    fmt = "{{.RestartCount}}|{{.Created}}|{{.State.StartedAt}}|{{.State.Running}}|{{.State.ExitCode}}"
    try:
        r = subprocess.run(
            ["docker", "inspect", "-f", fmt, name],
            capture_output=True, text=True, timeout=25,
            env={**os.environ, "MSYS_NO_PATHCONV": "1"},
        )
    except Exception:
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    parts = r.stdout.strip().split("|")
    if len(parts) < 5:
        return None
    return {
        "restarts": int(parts[0]),
        "created": parts[1],
        "started_at": parts[2],
        "running": parts[3] == "true",
        "exit_code": parts[4],
    }


def _age_seconds(iso: str) -> float | None:
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - d).total_seconds()
    except Exception:
        return None


def main() -> int:
    print("=== 容器重啟迴圈偵測（daily 15）===\n")

    prev: dict = {}
    if STATE.exists():
        try:
            prev = json.loads(STATE.read_text(encoding="utf-8")).get("containers", {})
        except Exception:
            prev = {}
    first_run = not prev

    now: dict = {}
    red, yellow, unknown = [], [], []

    print(f"  {'容器':<26}{'重啟數':>7}{'上次':>7}{'增加':>7}   判定")
    for name in CONTAINERS:
        info = _inspect(name)
        if info is None:
            unknown.append(name)
            print(f"  {name:<26}{'—':>7}{'—':>7}{'—':>7}   ？ 取不到（未驗）")
            continue
        now[name] = info
        p = prev.get(name)
        recreated = bool(p) and p.get("created") != info["created"]
        delta = None if (p is None or recreated) else info["restarts"] - p["restarts"]

        if not info["running"]:
            # ⚠️ `.State.ExitCode` 在有 restart policy 的容器上**不是那次崩潰的退出碼** ——
            #    它反映最後一次狀態轉換。2026-09-01 實測：inspect 回 0，
            #    而 `docker events` 現場捕捉到的是 **136（SIGFPE，原生程式碼硬當機）**。
            #    這裡標成「（僅供參考）」，不要讓讀的人拿它下結論。
            red.append(
                f"{name}：容器沒有在跑（inspect 回報 exit={info['exit_code']} —— "
                f"**僅供參考，restart policy 下這個欄位不是那次崩潰的碼**）"
            )
            verdict = "RED 沒在跑"
        elif recreated:
            verdict = "— 容器已重建（部署），基準重設"
        elif delta is None:
            verdict = "— 首次記錄，建立基準"
        elif delta > 0:
            red.append(f"{name}：自上次檢查以來又重啟 {delta} 次（累計 {info['restarts']}）")
            verdict = f"RED **又重啟 {delta} 次**"
        elif info["restarts"] > 0:
            age = _age_seconds(info["started_at"])
            if age is not None and age < RECENT_START_SECONDS:
                yellow.append(f"{name}：累計 {info['restarts']} 次，最近一次在 {age/60:.0f} 分鐘前")
                verdict = f"YELLOW 剛重啟過（{age/60:.0f} 分前）"
            else:
                verdict = "GREEN 未再增加"
        else:
            verdict = "GREEN"
        prev_n = p["restarts"] if p and not recreated else "—"
        print(f"  {name:<26}{info['restarts']:>7}{str(prev_n):>7}{str(delta if delta is not None else '—'):>7}   {verdict}")

    # 寫回狀態（即使這次判紅也要寫，否則下次會拿到過期基準而漏報）
    try:
        STATE.write_text(json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "containers": now,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"\n  ⚠ 狀態寫入失敗（下次會失去基準）：{exc}")

    print()
    if unknown and not now:
        print("  [YELLOW] 完全取不到容器狀態 —— **未驗**，不是「沒有重啟」")
        return 1
    if red:
        print(f"[RED] {len(red)} 項：")
        for x in red:
            print(f"  · {x}")
        print("\n  重啟迴圈的症狀是**間歇 502**，而 healthcheck 與公網探針在恢復後都是綠的。")
        print()
        print("  ⚠️ **取證不要用 `docker inspect`** —— 欄位名叫 `ExitCode`，但在有 restart")
        print("     policy 的容器上它反映的是最後一次狀態轉換，不是那次崩潰。")
        print("     2026-09-01 實測：inspect 回 **0**，現場捕捉是 **136（SIGFPE）** ——")
        print("     兩者導向完全相反的診斷（「主進程正常結束」vs「原生程式碼硬當機」）。")
        print()
        print("     正確作法（唯讀事件流，不影響服務）：")
        print("       docker events --filter container=<name> --filter event=die \\")
        print("         --format '{{.Time}} exit={{.Actor.Attributes.exitCode}}'")
        return 2
    if yellow:
        print(f"[YELLOW] {len(yellow)} 項剛重啟過（觀察中）：")
        for x in yellow:
            print(f"  · {x}")
        return 1
    if first_run:
        print("[GREEN] 首次執行，已建立基準（下次才比較得出增量）")
    else:
        print("[GREEN] 沒有容器在重啟迴圈")
    return 0


if __name__ == "__main__":
    sys.exit(main())
