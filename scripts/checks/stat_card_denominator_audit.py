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

## 怎麼知道它是綠的（負向對照紀錄）

GREEN 是空結果，而**空結果沒有內在證據可以證明自己是對的** ——
「沒有違規」與「偵測器壞了」在畫面上完全一樣。本支的鑑別力實證：

| 日期 | 注入什麼 | 結果 |
|---|---|---|
| 2026-08-29 | 把 `ERPVendorAccountsPage` 的 `data?.totals` 拿掉、改回逐筆累加 | GREEN → **RED**（行號正確）→ 還原後 GREEN |
| 2026-08-29 | 同上但**留一個樣板字串裡的 `totals`** | 首版（手寫剝除）**仍回綠**；改用 TS parser 後才 RED |

⚠️ 第二列是重點：它是**手寫正則版擋不掉的形態**。合成案例 8/8 全過而
真實檔案失敗過一次 —— **負向對照要打在真實檔案上**。

⚠️ 判準的**寬窄兩端**都被真實案例校正過：
首版 `items\.reduce` 漏掉 `pendingItems`（誤漏）；
首版掃 rglob 把詳情頁分頁也算進來（誤報）。兩次都是實測才發現。

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

# ⚠️ 剝除註解與字串**不自己寫**。
# 2026-08-29 手寫正則版被負向對照揭穿：`console.warn('後端未回傳 totals…')`
# 是**字串**，卻滿足了「有走後端彙總」的判準。補上引號字串之後又實測 7 種
# 形態，仍漏 **樣板字串／JSX 文字／多行樣板** —— 而 React 專案裡 JSX 文字
# 到處都是，等於這個洞一直開著。
#
# CK_AaaP 同日獨立踩到同一形狀（正則抓 `add_middleware(...)`，把註解掉的
# 與字串裡的都算進去，解析出 5 個而實際生效 3 個），並抽成他們的 L71。
# 兩個獨立來源、同一天、同一形狀 ⇒ 這是類別不是個案。結論：
# **不要自己寫剝除邏輯，用語言自己的解析器。**
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ts_source import code_only, TsToolUnavailable  # noqa: E402

CARD = re.compile(r"<(Statistic|ClickableStatCard)\b")
# 後端全量彙總的痕跡 —— 有任一個就代表這一頁知道要跟後端要總數
BACKEND_TOTAL = re.compile(r"\btotals\b|\bsummary_totals\b|\baggregates?\b|/totals\b")
# 在分頁陣列上累加
# ⚠️ 2026-08-29 放寬：首版寫 `\bitems\.reduce` —— 而真實變數叫 `pendingItems`，
# **「items」前面沒有單字邊界所以不匹配** ⇒ `ERPEInvoiceSyncPage` 的「待核銷金額」
# （當頁加總，而同一排的「待核銷發票」用的是全量 total）整個漏掉。
#
# 這是**誤漏**，與同日那幾個「判準命中散文」的誤報剛好是一體兩面：
# **判準的寬窄都要用真實案例校準，不能憑想像寫。**
# 改為比對「識別字**結尾**是 items/rows/list/dataSource」。
LOCAL_SUM = re.compile(
    r"\b\w*(?:[Ii]tems|[Rr]ows|[Ll]ist|dataSource)\s*\.\s*reduce\s*\("
    r"|for\s*\(\s*const\s+\w+\s+of\s+\w*(?:[Ii]tems|[Rr]ows|[Ll]ist|dataSource)\s*\)"
)


def main() -> int:
    if not PAGES.is_dir():
        print(f"✗ 找不到 {PAGES} —— 無法判定（不視為通過）")
        return 2

    # §2.6 的對象是**業務列表頁**，明文排除「詳情頁、儀表板、圖譜頁」。
    # ⚠️ 2026-08-29：首版掃 rglob（含子目錄）⇒ 把詳情頁的分頁也算進來。
    # `contractCase/tabs/VendorsTab` 的 `vendorList` 是 prop、無分頁
    # （一個案件的全部廠商），分母本來就是全體 —— 判它是誤報。
    # 收斂成「頁面根目錄」，與 weekly 56 對「業務列表頁」的定義一致。
    NOT_A_LIST = re.compile(r"(DetailPage|Dashboard|Hub|Scan|FormPage|CreatePage|EditPage)")
    candidates = [
        p for p in sorted(PAGES.glob("*.tsx"))
        if "__tests__" not in str(p) and ".test." not in p.name
        and not NOT_A_LIST.search(p.name)
    ]
    try:
        sources = code_only(candidates)
    except TsToolUnavailable as e:
        # 明確失敗，不退回較弱的判準 —— 「判準變弱」與「沒有違規」
        # 在輸出上長得一樣，那正是本檢核要防的東西（ADR-0028）。
        print(f"✗ 無法可靠剝除註解／字串：{e}")
        print("  刻意不退回手寫正則 —— 判準悄悄變弱與「沒有違規」在輸出上一樣。")
        return 2

    reds, scanned = [], 0
    for p in candidates:
        rel = str(p.relative_to(PAGES)).replace("\\", "/")
        t = sources.get(str(p.resolve()), "")
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

    # ⚠️ 措辭必須等於判準做了什麼。原本印「統計卡都走後端全量彙總」——
    # 而判準只查「有沒有在分頁陣列上 reduce/for-of」。用 `.map().filter().length`、
    # 用輔助函式、或用本支沒列的變數命名，都會通過而摘要照樣說「都走後端彙總」。
    # CK_AaaP 同日：**分類器正確，而人讀到的摘要說了別的事。**
    print("\n  （沒有偵測到「在分頁陣列上加總」的形態；"
          "本支不保證每張卡都讀後端 totals）")
    print("\nStatus: [GREEN] 統計卡分母正確")
    return 0


if __name__ == "__main__":
    sys.exit(main())
