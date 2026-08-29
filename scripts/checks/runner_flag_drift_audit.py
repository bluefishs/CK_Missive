#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""基線鎖有沒有真的被叫到：runner 呼叫時漏了啟用它的旗標。

## 為什麼有這一支（2026-08-29）

L99 記的是「**宣告的執行者不存在**」——`verify_architecture.py` 的白名單
寫著「由 pre-commit 與 CI 呼叫」，實查兩邊各 0 次。`grep -c` 就抓得到。

同日發現它的**下一個變形，而那個 grep 抓不到**：

  `alias_rls_coverage_audit.py` 的基線鎖（禁淨增）整段包在 `if args.ci:` 裡，
  而唯一的自動排程跑的 weekly 第 7 步**沒帶 `--ci`**
  （帶 `--ci` 的 `run_fitness.sh` 是手動月度觸發、不在 Windows 排程裡）。
  ⇒ 自 2026-05-19 建立起，那個鎖**一次都沒有真的鎖過**，
  而它允許淨增 29（實際 risks 已是 0，天花板高於地板 29 格）。

**執行者存在、腳本存在、旗標存在 —— 只是呼叫時少了那個旗標。**
三者分開看都是綠的。

## 判準（刻意收得很窄）

只抓「**基線回歸鎖**沒被啟用」這一種：

  RED  腳本 (a) 讀某個 `*_baseline*.json`／`.txt`
           (b) 有 `--ci`（或同義旗標）
           (c) 那個旗標**只在它成立時才做基線比對**（`if args.ci` 包住比對）
       而 runner 呼叫它時沒帶。

**刻意不抓 `--strict`**：`run_fitness_weekly.sh` 檔頭明文
「刻意不傳 --strict 給子腳本」（2026-08-03 決定，避免把 YELLOW 升成 RED，
例如 tender_freshness 的週末 stale）。那是**政策**不是疏漏，
一併判紅會產出 26 個假紅，而假紅會讓人開始無視這支。

首版粗判準實測 28 個命中，逐一判型後真問題只有 1 個（誤報率 96%）。
⇒ 這支的價值全在判準的窄度上。

## 誰跑它

weekly step 84（`run_fitness_weekly.sh`）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ROOT / "scripts" / "checks"
RUNNERS = [CHECKS / "run_fitness_weekly.sh", CHECKS / "run_fitness.sh"]

# 只看「啟用基線比對」的旗標；--strict 屬既有政策，見檔頭
GATE_FLAGS = ("--ci",)
# 比對區塊被旗標包住的形狀
GUARDED = re.compile(r"if\s+args\.ci\s*:")
BASELINE_REF = re.compile(r"[A-Za-z0-9_\-]*baseline[A-Za-z0-9_\-]*\.(json|txt)")


def _runner_calls():
    """{腳本檔名: {runner 檔名: set(已帶的旗標)}}"""
    calls: dict = {}
    for r in RUNNERS:
        if not r.is_file():
            continue
        t = r.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"scripts/checks/([a-z0-9_\-]+\.py)((?:\s+--[a-z\-]+)*)", t):
            calls.setdefault(m.group(1), {}).setdefault(r.name, set()).update(
                m.group(2).split()
            )
    return calls


def main() -> int:
    if not CHECKS.is_dir():
        print(f"✗ 找不到 {CHECKS} —— 無法判定（不視為通過）")
        return 2

    calls = _runner_calls()
    if not calls:
        print("✗ 從 runner 解析不到任何腳本呼叫 —— runner 格式可能變了，本檢核已失效")
        return 2

    reds, checked = [], 0
    for script, by_runner in sorted(calls.items()):
        p = CHECKS / script
        if not p.is_file():
            continue
        src = p.read_text(encoding="utf-8", errors="ignore")
        # (a) 讀基線 (b) 有 --ci (c) 比對被 --ci 包住
        if not BASELINE_REF.search(src):
            continue
        if '"--ci"' not in src and "'--ci'" not in src:
            continue
        if not GUARDED.search(src):
            continue          # 比對不受旗標控制 ⇒ 不帶也會做，不算漏
        checked += 1
        for runner, flags in by_runner.items():
            if not any(f in flags for f in GATE_FLAGS):
                reds.append((script, runner))

    print("=" * 74)
    print("基線鎖有沒有真的被叫到（runner 漏旗標，weekly 84）")
    print("=" * 74)
    print(f"\n  檢視 {checked} 支「基線比對受旗標控制」的腳本")

    if checked == 0:
        print("\n✗ 一支都沒掃到 —— 腳本結構或旗標命名可能變了，本檢核已失效")
        return 2

    for script, runner in reds:
        print(f"\n  [RED  ] {runner} 呼叫 {script} 時沒帶 --ci")
        print("           該腳本的基線比對整段包在 `if args.ci:` 裡 ⇒ **不帶就完全不比對**。")
        print("           腳本在、排程在、旗標也在 —— 三者分開看都是綠的，")
        print("           而那個鎖從來沒有真的鎖過（alias_rls 是這樣過了三個月）。")

    if reds:
        print(f"\nStatus: [RED] {len(reds)} 處基線鎖沒有被啟用")
        return 1

    print("\n  （受旗標控制的基線比對，runner 都有帶旗標）")
    print("\nStatus: [GREEN] 基線鎖都有被叫到")
    return 0


if __name__ == "__main__":
    sys.exit(main())
