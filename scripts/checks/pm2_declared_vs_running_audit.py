#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PM2 宣告了什麼 vs PM2 實際在跑什麼（2026-08-27）。

## 為什麼有這一支

2026-08-27 人工盤點才發現：`ecosystem.config.js` 宣告三支
（health-watchdog / synthetic-baseline / invoice-watcher），
而 `pm2 jlist` 上**一支都沒有在跑** —— 那 14 支全部屬於別的 repo。

逐支核實後，其中兩支的功能已遷入容器內排程（synthetic_baseline_inject
有 257 次執行紀錄、einvoice_sync 條件式註冊），**但 health-watchdog 沒有等價物**：

    容器 healthcheck = curl -f /health，30s、retries 3   → 只會把容器標成 unhealthy
    restart policy   = always                            → 只在**程序結束**時作用

**Docker 不會因為 unhealthy 就重啟容器**（那需要 autoheal 之類的外掛）。
所以一個「還活著但卡住」的 backend 會停在 unhealthy 不動，直到有人看到。
「N 容器 0 非健康」量的是**狀態**，不是**復原能力**。

而記憶裡早就寫著這件事會發生：`pm2_layer_no_liveness_sentinel.md`
——「PM2 是第三個排程層、只有註冊覆蓋沒有執行結果哨兵」。它預言的事發生了，
而沒有任何東西在問。

## 判準：宣告與現實不一致就出聲，不管往哪個方向解決

刻意**不用 baseline**：這支的所有項目都是「等一個決定」，而決定一旦做出
（把它跑起來／或從 ecosystem.config.js 拿掉），這支就自然變綠。
用 baseline 反而會讓「還沒決定」永遠看起來像已處理。

判 YELLOW 不判 RED：宣告與現實不一致是治理問題不是系統故障 ——
系統現在是好的，缺的是「說的和做的一致」。

退出碼：0=GREEN／1=YELLOW／2=RED（全 portfolio 一致）
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
ECOSYSTEM = ROOT / "ecosystem.config.js"


def declared_apps() -> list[str]:
    """從 ecosystem.config.js 取出宣告的 app 名稱。

    用 node 解析而不是 regex —— 那是一個真的 JS 模組，
    regex 會在有人改寫成變數或展開時安靜地少抓（本專案已記過同型）。
    """
    if not ECOSYSTEM.is_file():
        return []
    try:
        r = subprocess.run(
            ["node", "-e",
             f"const c=require({json.dumps(str(ECOSYSTEM))});"
             "process.stdout.write(JSON.stringify((c.apps||[]).map(a=>a.name)))"],
            capture_output=True, timeout=20, cwd=str(ROOT),
            encoding="utf-8", errors="replace",
        )
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout)
    except Exception:
        pass
    # node 不可用時的後備：明說是後備，不要讓它看起來像正常路徑
    print("  [WARN] node 不可用，改用正則解析（可能少抓）")
    txt = ECOSYSTEM.read_text(encoding="utf-8", errors="ignore")
    return re.findall(r"name:\s*'([^']+)'", txt)


def running_apps() -> tuple[dict[str, str], bool]:
    """回 ({name: status}, pm2 是否可用)。

    ⚠️ Windows 上 pm2 是 `pm2.cmd`，`subprocess.run(["pm2", ...])` 不帶 shell
    **找不到它** —— 第一版就是這樣，結果每次都走「pm2 不可用 → SKIP」。
    而**永遠 SKIP 的檢核比沒有這支更糟**：它在清單上看起來像有覆蓋，
    實際上從來沒有判過任何事（本專案反覆記的假綠家族）。
    所以這裡逐一試，並且**試完全部才說不可用**。
    """
    # ⚠️ 明確指定 encoding="utf-8"：`text=True` 會用系統預設（本機是 cp950），
    #   而 pm2 的輸出含 UTF-8 ⇒ UnicodeDecodeError，然後這支就「pm2 不可用」。
    #   同 L92：檢核在**要說話的那一刻**崩掉，而平常看起來好好的。
    import shutil
    candidates = ["pm2", "pm2.cmd", shutil.which("pm2"), shutil.which("pm2.cmd")]
    for exe in [c for c in candidates if c]:
        try:
            r = subprocess.run([exe, "jlist"], capture_output=True, timeout=30, shell=False,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0 and r.stdout.strip().startswith("["):
                data = json.loads(r.stdout)
                return {p["name"]: p.get("pm2_env", {}).get("status", "?") for p in data}, True
        except Exception:
            continue
    # 最後才用 shell（Windows 上 .cmd 需要它）
    try:
        r = subprocess.run("pm2 jlist", capture_output=True, timeout=30, shell=True,
                           encoding="utf-8", errors="replace")
        if r.returncode == 0:
            out = r.stdout[r.stdout.find("["):] if "[" in r.stdout else ""
            if out.strip().startswith("["):
                data = json.loads(out)
                return {p["name"]: p.get("pm2_env", {}).get("status", "?") for p in data}, True
    except Exception:
        pass
    return {}, False


def main() -> int:
    print("=" * 62)
    print("PM2 宣告 vs 實際在跑")
    print("=" * 62)

    declared = declared_apps()
    running, pm2_ok = running_apps()

    if not pm2_ok:
        # 探測不到就不下結論 —— 「pm2 用不了」與「宣告的都沒在跑」
        # 在結論上長得一樣，但意思完全不同（2026-08-21 立的判準）。
        #
        # 2026-09-02：判準是對的，**退出碼錯了**。原本 return 0 ⇒ 探測不到時
        # 在 weekly 上顯示為 GREEN，而本檔 docstring 自己就寫著
        # 「永遠 SKIP 的檢核比沒有這支更糟：它在清單上看起來像有覆蓋」——
        # 它知道這個危險，然後它自己就是那樣。
        #
        # 當天實測揭穿它：`pm2 jlist` 的輸出被 "[PM2] Spawning PM2 daemon..."
        # 污染且退出碼 1（另一個 session 在同一台機器上留下孤兒 daemon），
        # 於是同一個原因讓 pm2_process_liveness_audit 報 RED、本支報 GREEN。
        # **同一個事實，兩支檢核給出相反的燈號。**
        #
        # 改回 1（YELLOW）：三態約定 0=GREEN / 1=YELLOW / 2+=RED，
        # 而「我看不到」就是 YELLOW —— 不是通過，也不是故障（L133）。
        print("  [YELLOW] pm2 不可用（未安裝或無法執行）—— **未驗**，不是「都在跑」")
        print("     常見成因：pm2 jlist 輸出被 daemon spawn 訊息污染而退出碼非 0；")
        print("     若剛有別的工具呼叫過 pm2，可能留下孤兒 daemon（重開機會清掉）。")
        return 1

    if not declared:
        print("  [SKIP] ecosystem.config.js 沒有宣告任何 app")
        return 0

    print(f"  宣告 {len(declared)} 支｜PM2 上共 {len(running)} 支程序")
    print()

    missing = []
    for name in declared:
        st = running.get(name)
        if st is None:
            missing.append((name, "不在 PM2 清單上"))
            print(f"  ✗  {name:<24} 不在 PM2 清單上")
        elif st != "online":
            missing.append((name, st))
            print(f"  ✗  {name:<24} 狀態 = {st}")
        else:
            print(f"  ✓  {name:<24} online")

    print()
    if not missing:
        print("  [GREEN] ecosystem.config.js 宣告的都在跑")
        return 0

    print(f"  [YELLOW] {len(missing)} 支宣告了但沒有在跑")
    print()
    print("  說的與做的不一致。兩個方向都能讓它變綠，選一個：")
    print("    · 真的要它跑  → pm2 start ecosystem.config.js --only <name>")
    print("    · 已被取代    → 從 ecosystem.config.js 移除，並在檔頭寫明誰接手了")
    print()
    print("  ⚠️ 檔頭已記錄 2026-08-27 的逐支核實結果（誰接手、誰沒有等價物）。")
    print("     其中 health-watchdog 的「假死自動復原」目前是空的 ——")
    print("     Docker 不會因為 unhealthy 就重啟容器，restart:always 只在程序結束時作用。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
