#!/usr/bin/env python3
"""weekly 執行結果的統整與歸納 —— owner 2026-09-09：「weekly 要統整與歸納」。

## 為什麼需要它

weekly 已經 131 步，而它的輸出是**逐步流水帳**。2026-09-09 那次跑完的實況：

    127 步 → 綠 83、rc=1 25 支、rc=2 19 支

**44 支非綠**攤在 127 行裡，人看不出哪些重要、哪些是老問題、哪些是這週新壞的。
更關鍵的是趨勢：

    08-30   94 步   綠 79   非綠 15
    09-06  111 步   綠 73   非綠 38
    09-09  127 步   綠 83   非綠 44

⇒ 三週加了 33 步，非綠增加 29。**新檢核幾乎是一上線就紅，而紅燈沒有人在清。**
本 repo 早記過「永遠是紅的訊號與沒有訊號是同一個下場」——那正是現在的狀態。

## 這支做什麼

讀 `wiki/memory/fitness_step_history.jsonl` 的 weekly 紀錄，輸出三段歸納：

  ① **按領域**：每個領域綠／黃／紅幾支（領域定義在 `weekly_step_taxonomy.json`）
  ② **按壽命**：從來沒綠過（＝永久紅燈，等於沒有訊號）／本週新紅（＝真的變壞了）
  ③ **未分類**：taxonomy 沒登記的步號 —— 這是兩份宣告分家的守門

## 判準

  * 有「本週新紅」⇒ rc=2（**這是唯一代表「這週真的變壞了」的訊號**）
  * 只有未分類步號 ⇒ rc=2（分類與 runner 分家，彙總從此開始失真）
  * 其餘 ⇒ rc=0，但永久紅燈的數量會印出來，那是待清的存量不是本週的事故

⚠️ **刻意不把「有紅燈」判成紅**：131 步裡有 19 支 rc=2 是存量，
每週報一次同樣的 19 支只會讓人不再看它。要看存量請讀 ② 的清單。
"""
from __future__ import annotations

import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HIST = os.path.join(ROOT, "wiki", "memory", "fitness_step_history.jsonl")
TAX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weekly_step_taxonomy.json")


def step_no(key: str):
    """紀錄的鍵是「<步號> <描述>」。取步號。"""
    head = key.split(" ", 1)[0]
    return int(head) if head.isdigit() else None


def analyse(runs, tax):
    """純函式：給定 weekly 紀錄與分類，回 (新紅, 從未綠, 未分類)。

    抽出來是為了 `--self-test` 能在**不依賴真實歷史檔**的情況下驗四種情境 ——
    2026-09-09 首次正向控制時，「未分類」與「本週新紅」同時成立，
    退出碼都是 2，**分不出是哪一個判準在作用**。判準要能單獨驗證。
    """
    step2dom = {}
    for dom, nums in tax.items():
        for n in nums:
            step2dom[n] = dom
    steps = runs[-1]["steps"]
    unclassified = [k for k in steps if step2dom.get(step_no(k)) is None]
    hist = {}
    for r in runs:
        for k, v in r["steps"].items():
            hist.setdefault(step_no(k), []).append(v)
    never_green = sorted(n for n, vs in hist.items()
                         if n is not None and len(vs) >= 3 and all(v != 0 for v in vs))
    prev_by_no = {step_no(k): v for k, v in (runs[-2]["steps"] if len(runs) >= 2 else {}).items()}
    new_red = [(step_no(k), k, v) for k, v in steps.items()
               if v != 0 and prev_by_no.get(step_no(k)) == 0]
    return new_red, never_green, unclassified


def self_test() -> int:
    """四種情境的負向與正向控制。"""
    TAX = {"A": [1, 2]}
    def run(ts, kv):
        return {"ts": ts, "runner": "weekly", "steps": {("%d x" % k): v for k, v in kv.items()}}
    cases = [
        ("全綠、分類完整 ⇒ 無新紅、無未分類",
         [run("t1", {1: 0, 2: 0}), run("t2", {1: 0, 2: 0})], TAX, 0, 0),
        ("上次綠這次紅 ⇒ 抓到 1 支新紅",
         [run("t1", {1: 0, 2: 0}), run("t2", {1: 2, 2: 0})], TAX, 1, 0),
        ("一直都紅（上次也紅）⇒ 不算新紅（那是存量）",
         [run("t1", {1: 2, 2: 0}), run("t2", {1: 2, 2: 0})], TAX, 0, 0),
        ("多了沒登記的步號 ⇒ 抓到 1 支未分類",
         [run("t1", {1: 0, 2: 0}), run("t2", {1: 0, 2: 0, 9: 0})], TAX, 0, 1),
    ]
    ok = True
    print("=== weekly_summary_rollup 自測 ===")
    for name, runs, tax, want_red, want_unc in cases:
        nr, _ng, unc = analyse(runs, tax)
        good = (len(nr) == want_red and len(unc) == want_unc)
        ok = ok and good
        print("  %s %s（新紅 %d/%d、未分類 %d/%d）"
              % ("✅" if good else "⛔", name, len(nr), want_red, len(unc), want_unc))
    print("自測 %s" % ("通過" if ok else "失敗"))
    return 0 if ok else 2


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not os.path.isfile(HIST):
        print("找不到 %s" % HIST)
        return 1
    runs = []
    for line in io.open(HIST, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("runner") == "weekly":
            runs.append(r)
    if not runs:
        print("沒有任何 weekly 執行紀錄 —— 無法歸納。")
        print("⚠️ 這不是綠燈：它代表 weekly 從來沒跑過，或紀錄沒寫進去。")
        return 1

    tax = json.load(io.open(TAX, encoding="utf-8"))["domains"]
    step2dom = {}
    for dom, nums in tax.items():
        for n in nums:
            step2dom[n] = dom

    last = runs[-1]
    steps = last["steps"]

    print("=" * 68)
    print("weekly 統整與歸納")
    print("=" * 68)
    print("最近一次：%s（%d 步）" % (last["ts"], len(steps)))
    print()

    # ---- ① 按領域 ----
    agg = {d: [0, 0, 0] for d in tax}          # 綠 / rc1 / rc2
    unclassified = []
    for k, v in steps.items():
        n = step_no(k)
        dom = step2dom.get(n)
        if dom is None:
            unclassified.append(k)
            continue
        idx = 0 if v == 0 else (1 if v == 1 else 2)
        agg[dom][idx] += 1

    print("① 按領域")
    print("   %-22s %5s %5s %5s   %s" % ("領域", "綠", "黃", "紅", "健康度"))
    for dom in sorted(agg, key=lambda d: -(agg[d][1] + agg[d][2])):
        g, y, r = agg[dom]
        tot = g + y + r
        if tot == 0:
            continue
        if tot < 3:
            # ⚠️ 小樣本不畫健康度：首版讓「統計與畫面一致性」顯示 0%，
            # 而那個領域當時只有 2 支有紀錄（另兩支是這週才加、上次還沒跑）。
            # **一個看起來很糟的百分比，實際上是樣本不足** —— 那會讓人去修沒壞的東西。
            print("   %-22s %5d %5d %5d   （只有 %d 支有紀錄，不計健康度）" % (dom, g, y, r, tot))
            continue
        bar = "█" * int(round(g / tot * 10)) + "·" * (10 - int(round(g / tot * 10)))
        print("   %-22s %5d %5d %5d   %s %d%%" % (dom, g, y, r, bar, round(g / tot * 100)))
    print()

    # ---- ② 按壽命 ----
    hist = {}
    for r in runs:
        for k, v in r["steps"].items():
            hist.setdefault(step_no(k), []).append(v)
    never_green = sorted(n for n, vs in hist.items()
                         if n is not None and len(vs) >= 3 and all(v != 0 for v in vs))
    prev = runs[-2]["steps"] if len(runs) >= 2 else {}
    prev_by_no = {step_no(k): v for k, v in prev.items()}
    new_red = []
    for k, v in steps.items():
        n = step_no(k)
        if v != 0 and prev_by_no.get(n) == 0:
            new_red.append((n, k, v))

    name_by_no = {step_no(k): k for k in steps}
    print("② 按壽命")
    print("   本週新紅（上次綠、這次不綠）：%d 支" % len(new_red))
    for n, k, v in sorted(new_red):
        print("      rc=%s  %s  [%s]" % (v, k[:56], step2dom.get(n, "未分類")))
    print("   從來沒綠過（跑過 ≥3 次）：%d 支 —— 永久紅燈等於沒有訊號" % len(never_green))
    for n in never_green:
        print("      %s  [%s]" % ((name_by_no.get(n) or str(n))[:56], step2dom.get(n, "未分類")))
    print()

    # ---- ③ 未分類 ----
    print("③ 分類覆蓋")
    if unclassified:
        print("   ⛔ taxonomy 沒登記的步號：%d 支" % len(unclassified))
        for k in unclassified:
            print("      %s" % k[:60])
        print("   ⇒ 新增 run_step 要同步登記進 weekly_step_taxonomy.json，")
        print("      否則這份歸納會安靜地漏掉它（兩份宣告分家）。")
    else:
        print("   ✅ 全部步號都有領域")
    print()

    # ---- 趨勢 ----
    print("④ 趨勢（最近 %d 次）" % min(4, len(runs)))
    for r in runs[-4:]:
        s = r["steps"]
        g = sum(1 for v in s.values() if v == 0)
        print("   %s  步數 %-4d 綠 %-4d 非綠 %d" % (r["ts"][:16], len(s), g, len(s) - g))
    print()

    if new_red:
        print("⛔ 本週有新紅 %d 支 —— 那是這週真的變壞的東西，先看它們。" % len(new_red))
        return 2
    if unclassified:
        print("⛔ 有未分類步號，彙總從此會失真。")
        return 2
    print("✅ 本週沒有新紅（存量紅燈 %d 支見 ②，那是待清不是本週事故）" % len(never_green))
    return 0


if __name__ == "__main__":
    sys.exit(main())
