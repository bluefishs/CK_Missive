#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""統計卡的分母必須是全體，不能是當頁（development-rules §2.6 ①）。

## 為什麼有這一支

owner 2026-08-29 裁示：「具備統計圖卡與列表互動篩選機制，且皆以當年度
為統計基準」。我把它寫進 `development-rules.md` §2.6，**但沒有寫守門** ——
而本 repo 反覆記過的正是「規範寫了、沒有機制強制」（型別 SSOT 累積出
18 個違規無人知曉；腳本存在 ≠ 有在強制）。這一支補上 §2.6 的第 ① 條。

## 這個 bug 長什麼樣

前端在**分頁後的陣列**上做加總：

    for (const item of items) { total += item.amount; }   // items 是當頁

實測後果：發票彙總卡只算 20/48 筆，顯示 1,892,988 而正確值 7,258,898
（**少 74%**）。而它不會報錯 —— 畫面上的數字看起來完全正常。

⚠️ 更難發現的是「**碰巧對**」：`/erp/vendor-accounts` 現況 16 家廠商、
每頁 20 筆 ⇒ 卡片數字是對的，但那是巧合。資料一超過一頁就靜靜開始少算。
**這一支要抓的是那個形狀，不是當下的數字對不對。**

## 判準

業務列表頁（有 `dataIndex`）且畫了 `Statistic` / `ClickableStatCard`：

  RED  在分頁陣列（items/rows/dataSource/filtered*）上 reduce/for-of 累加，
       **且檔內完全沒有** totals / summary / statistics 之類的後端彙總欄位

  ok   讀後端 totals（允許 fallback —— 但 fallback 應出聲，那由 ADR-0028 管）

刻意用「檔內有沒有後端彙總」當豁免條件而不是逐行分析資料流：
靜態分析追不到 `stats.totalPayable` 是從哪來的，而「這一頁到底有沒有
跟後端要全量」是可靠且不會誤判的代理問題。

## 誰跑它

weekly step 82（`run_fitness_weekly.sh`）。
"""
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "frontend" / "src" / "pages"

COMMENT = re.compile(r"/\*[\s\S]*?\*/|//[^\n]*")
# ⚠️ 註解**與字串字面值**都要先去掉再比對。
# 2026-08-29 負向對照當場揭穿：注入回歸後本檢核仍回綠，因為該檔的
# `console.warn('後端未回傳 totals…')` 是**字串**，滿足了「有走後端彙總」。
# 同一天已經在 weekly 81 與 weekly 56 各犯過一次（那兩次是註解）——
# **凡是用字串比對判斷程式碼行為，說明文字與訊息文字都會冒充程式碼。**
STRING = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"")


def _strip(src: str) -> str:
    return STRING.sub("''", COMMENT.sub("", src))
CARD = re.compile(r"<(Statistic|ClickableStatCard)\b")
# 後端全量彙總的痕跡 —— 有任一個就代表這一頁知道要跟後端要總數
BACKEND_TOTAL = re.compile(r"\btotals\b|\bsummary_totals\b|\baggregates?\b|/totals\b")
# 在分頁陣列上累加
LOCAL_SUM = re.compile(
    r"\b(?:items|rows|dataSource|filtered\w*)\s*\.\s*reduce\s*\("
    r"|for\s*\(\s*const\s+\w+\s+of\s+(?:items|rows|dataSource|filtered\w*)\s*\)"
)


def main() -> int:
    if not PAGES.is_dir():
        print(f"✗ 找不到 {PAGES} —— 無法判定（不視為通過）")
        return 2

    reds, scanned = [], 0
    for p in sorted(PAGES.rglob("*.tsx")):
        rel = str(p.relative_to(PAGES)).replace("\\", "/")
        if "__tests__" in rel or ".test." in p.name:
            continue
        t = _strip(p.read_text(encoding="utf-8", errors="ignore"))
        if "dataIndex" not in t or not CARD.search(t):
            continue
        scanned += 1
        if BACKEND_TOTAL.search(t):
            continue
        m = LOCAL_SUM.search(t)
        if m:
            line = t[: m.start()].count("\n") + 1
            reds.append((rel, line, m.group(0).strip()[:60]))

    print("=" * 74)
    print("統計卡分母：必須是全體不是當頁（development-rules §2.6 ①，weekly 82）")
    print("=" * 74)
    print(f"\n  掃描 {scanned} 個有統計卡的業務列表頁")

    if scanned == 0:
        print("\n✗ 一個都沒掃到 —— 頁面結構或元件命名可能變了，本檢核已失效")
        return 2

    for rel, line, frag in reds:
        print(f"\n  [RED  ] pages/{rel}:{line}")
        print(f"           {frag}")
        print("           卡片數字從分頁後的陣列算出來 ⇒ 資料超過一頁就靜靜少算。")
        print("           改法：後端多回一個 totals（分頁前計算），前端讀它。")
        print("           參考 `client_receivable_repository` / `ledger_repository.sum_by_filters`。")

    if reds:
        print(f"\n⚠️ 這一類的危險不在「現在算錯了」，而在**它會在資料長大時才開始錯**，")
        print("   且畫面上的數字看起來一樣正常。實測案例：發票彙總卡少 74%。")
        print(f"\nStatus: [RED] {len(reds)} 個統計卡用當頁當分母")
        return 1

    print("\n  （統計卡都走後端全量彙總）")
    print("\nStatus: [GREEN] 統計卡分母正確")
    return 0


if __name__ == "__main__":
    sys.exit(main())
