#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""紅很久的步驟必須有名字 —— 沒有人收的訊號要看得出來「沒有人收」。

## 為什麼有這一支

owner 2026-08-30 的目標：**不要再發生每個 session 各自創、無整合運用**。

「無整合運用」最直接的表現不是缺機制，是**機制在響而沒有人收**。實測
（`wiki/memory/fitness_step_history.jsonl` 近 8 輪）：

    最近一輪 89 步 → 綠 73（82%）／紅 8／黃 8
    **每一輪都非綠的：11 支**
    近 8 輪從來沒紅過的：65 支

那 11 支逐一查過，**沒有一支是壞掉的檢核**，每一支都是真發現、
而且檢核自己就寫明了處置方式：

    · 廠商合約經費 CK2026_PM_01_005 填 $3 而應付 $159,000（填報錯誤）
    · 2 個 admin 未綁 SSO ⇒ 密碼登入已回 410，**現在就登不進來**
    · 帳本有真的漏帳
    · PM2 宣告了但沒在跑

⇒ 它們不是噪音，是**沒有人收**。而問題在於：
**紅了 8 週的訊號，和今天才紅的，在畫面上長得一模一樣。**

## 這一支不重複判斷那些內容

它只問一件事：**這個長期紅燈有沒有名字？**

有名字 ＝ 在 `.chronic_red_registry.json` 裡登記，且說明
「為什麼它還紅著」「誰要決定」「追到哪一個待辦編號」。

* 已登記 → 印出來（含追蹤編號），**不判紅**
* **未登記的新長期紅燈 → RED** ⇒ 它必須被命名，或被修好

⚠️ 這不是把紅燈變綠的手段。原本那 11 支**照樣各自紅著**，
本支只是讓「有多少紅燈是沒有人在收的」這件事本身變得看得見。

## 為什麼不做「合流為四大雷達」

owner 提供的藍圖建議把 90+ 步聚合成 4 個雷達燈號。實測反對這個作法：

* 問題**不是步數太多** —— 82% 是綠的，65 支從來沒響過。
* 噪音來自那 11 支慢性紅燈；聚合之後它們會讓對應雷達**永遠黃／紅**，
  狼來了照舊，而 65 支有鑑別力的檢核**失去身分**。
* 今天所有可行動的發現都來自**具體點名**
  （「id=72/73 各 50 萬沒有帳本分錄」）。變成「財務雷達＝黃」就無法行動。

## 誰跑它

weekly step 94（`run_fitness_weekly.sh`）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root, wiki_memory_dir  # noqa: E402

HISTORY = wiki_memory_dir() / "fitness_step_history.jsonl"
REGISTRY = repo_root() / "scripts" / "checks" / ".chronic_red_registry.json"

# 連續幾輪非綠才算「長期」。4 輪 ≈ 一個月的 weekly。
CHRONIC_RUNS = 4
# 只看最近幾輪 —— 更早的與現況無關
WINDOW = 8


def load_runs() -> list[dict]:
    if not HISTORY.is_file():
        return []
    out = []
    for line in HISTORY.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def find_chronic(runs: list[dict]) -> dict[str, int]:
    """回 {步驟名: 連續非綠輪數}（只算最近 WINDOW 輪內、每輪都非綠者）。"""
    window = runs[-WINDOW:]
    seen: dict[str, int] = {}
    red: dict[str, int] = {}
    for r in window:
        for k, v in (r.get("steps") or {}).items():
            seen[k] = seen.get(k, 0) + 1
            if v != 0:
                red[k] = red.get(k, 0) + 1
    return {
        k: red[k] for k in red
        if red[k] == seen[k] and seen[k] >= CHRONIC_RUNS
    }


def main() -> int:
    print("=" * 74)
    print("長期紅燈必須有名字（weekly 94）")
    print("=" * 74)

    runs = load_runs()
    if len(runs) < CHRONIC_RUNS:
        print(f"\n✗ 只有 {len(runs)} 輪歷史（需要 ≥{CHRONIC_RUNS}）—— 無法判定，不視為通過")
        return 2

    chronic = find_chronic(runs)
    known = {}
    if REGISTRY.is_file():
        known = json.loads(REGISTRY.read_text(encoding="utf-8")).get("known", {})

    print(f"\n  歷史 {len(runs)} 輪｜檢視最近 {min(WINDOW, len(runs))} 輪")

    # ⚠️ 2026-08-30：**本支結構上永遠慢一輪，這件事必須說出來。**
    #
    # `run_fitness_weekly.sh` 把逐步結果寫進歷史是在 step 94 **之後** ——
    # 所以這裡看到的視窗**不含本輪自己**。後果不是理論的：本輪 step 51
    # 剛剛才轉綠，而本支仍以「連續 5 輪非綠」把它報成未登記的長期紅燈。
    #
    # 不改寫入時機（那會讓歷史的語意變成「跑到一半的結果」），
    # 改成明講落差 —— 同 `observed_span()` 的作法：
    # **凡是拿歷史歸因，先講「我看得到多遠」。**
    win = runs[-WINDOW:]
    if win:
        first, last = win[0].get("ts", "?"), win[-1].get("ts", "?")
        manual_n = sum(1 for r in win if r.get("manual"))
        print(f"  視窗：{first[:19]} ～ {last[:19]}"
              f"（其中手動跑 {manual_n} 輪）")
        print("  ⚠️ **不含本輪** —— 逐步結果在 step 94 之後才寫入歷史。"
              "本輪剛轉綠的步驟仍會在此被報成長期紅燈，下一輪才會消失。")

    print(f"  連續 {CHRONIC_RUNS}+ 輪非綠：{len(chronic)} 支｜已登記 {len(known)} 支")

    registered = [k for k in chronic if k in known]
    orphan = [k for k in chronic if k not in known]

    if registered:
        print("\n  ── 已登記（有人在追，不判紅）──")
        for k in sorted(registered, key=lambda x: int(x.split()[0]) if x.split()[0].isdigit() else 999):
            e = known[k]
            print(f"    · {k[:44]:<46} → {e.get('tracked_as', '?')}")
            if e.get("why"):
                print(f"         {e['why'][:88]}")

    for k in sorted(orphan):
        print(f"\n  [RED  ] {k}")
        print(f"           連續 {chronic[k]} 輪非綠而**沒有登記** —— "
              f"它在響，而看不出來有沒有人在收。")
        print("           處置二選一：修好它，或在 .chronic_red_registry.json 登記")
        print("           （寫明為什麼還紅著、誰要決定、追到哪個待辦編號）。")

    # 已登記但已經轉綠的 —— 該從登記裡移除，否則登記本身會過期
    stale = [k for k in known if k not in chronic]
    if stale:
        print("\n  ── 登記了但已不再長期紅（該移除，否則登記會過期）──")
        for k in stale:
            print(f"    · {k}")

    if orphan:
        print(f"\n⚠️ 紅了很久的訊號與今天才紅的，在畫面上長得一模一樣 ——")
        print("   而前者代表「沒有人收」，那是比單一故障更該知道的事。")
        print(f"\nStatus: [RED] {len(orphan)} 支長期紅燈沒有名字")
        return 2
    if stale:
        print(f"\nStatus: [YELLOW] {len(stale)} 筆登記已過期（步驟已轉綠）")
        return 1
    print(f"\nStatus: [GREEN] {len(chronic)} 支長期紅燈皆已登記追蹤")
    return 0


if __name__ == "__main__":
    sys.exit(main())
