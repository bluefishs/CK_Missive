#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""§2.6 列表頁三要素的守門：① 統計卡分母＝全體　③ 年度篩選預設當年度。

（② 互動篩選**刻意不做** —— `Statistic` 用在很多不該互動的地方，
一律判紅只會產出整片噪音。理由與 `frontend_design_standard_audit` 同。）

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
| 2026-08-30 | 拿掉 `ERPInvoiceSummaryPage` 的預設當年度 | GREEN → **RED**（指名該檔）→ 還原後 GREEN |
| 2026-08-30 | 拿掉 `ERPOperationalListPage` 年度 Select 的 `value` 綁定 | GREEN → **RED** → 還原後 GREEN |

## ③ 的判準為何以「有沒有 setter」為進場條件（2026-08-30）

**這一條的違規形狀是「那個 key 不存在」**，而我的第一版判準去問
「`year` 的初始值對不對」—— 對「params 裡根本沒有 `year`」完全是盲的，
於是量出「0 違規」。實際上盲區裡就躺著兩個真的：

| 頁面 | 初始 params | 後果 |
|---|---|---|
| `ERPInvoiceSummaryPage` | `{skip:0,limit:20}` | 年度 Select 開場空的 ⇒ **歷年混算** |
| `ERPOperationalListPage` | `fiscal_year` 未設 | 同上 |

⇒ 進場條件改成「**有沒有人在寫入年度**」（setter 存在＝這頁有年度篩選），
再問「預設值在不在」。**用「有沒有人要改它」證明欄位該存在，
比用「欄位長什麼樣」可靠。**

⚠️ 同時查了「篩了卻不顯示」：`ERPOperationalListPage` 的年度 Select
只有 `onChange` 沒有 `value` —— 我加預設值時**差點造出隱形篩選**
（資料被篩而畫面說未選，比不篩更糟）。故 ③ 一併查 `value` 綁定。

⚠️ 第二列是重點：它是**手寫正則版擋不掉的形態**。合成案例 8/8 全過而
真實檔案失敗過一次 —— **負向對照要打在真實檔案上**。

⚠️ 判準的**寬窄兩端**都被真實案例校正過：
首版 `items\.reduce` 漏掉 `pendingItems`（誤漏）；
首版掃 rglob 把詳情頁分頁也算進來（誤報）。兩次都是實測才發現。

## 收窄到「根目錄頁面」的代價已實測 —— 是零（2026-08-29 晚）

同日稍早發現 `/pm/cases/509` 的報價單合計顯示錯誤（35,000 顯示成 1,750），
而那個元件在**子目錄**（`pages/erpQuotation/QuotationItemsTab.tsx`）
⇒ 合理的懷疑是「上面那個收窄放過了真問題」。

**實測反駁了這個懷疑**：拿同一套判準掃全部 158 個子目錄頁面，
命中 **1 個**，正是已知的誤報 `contractCase/tabs/VendorsTab`。
⇒ 收窄沒有藏起任何真問題，維持現狀。

那個 509 的 bug 漏掉的原因是**另一個**：它的錯數字在 `Table.Summary`
裡，不是 `<Statistic>` 卡片。而全庫「畫了 Table 合計列且含金額」的元件
**只有 2 個**（509 那個＋`taoyuan/PaymentsTab`，後者取全量且
`total_budget` 來自後端，是對的）⇒ **為這個形狀加判準會是零命中**，
不加。這裡寫下來是為了不用再查第二次。

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

# ── §2.6 ③：預設當年度 ────────────────────────────────────────────────
# 「這一頁有年度篩選」的證據＝**有人在寫入年度**（setter），因為字串
# （`placeholder="年度"`）會被 code_only 剝掉，識別字才留得下來。
YEAR_SETTER = re.compile(r"\b(?:set\w*[Yy]ear\w*\s*\(|\b(?:fiscal_year|year)\s*:\s*v\b)")
# 預設值的兩種合法形狀：獨立 state，或包在 params 物件裡
YEAR_STATE = re.compile(r"const\s*\[\s*\w*[Yy]ear\w*\s*,\s*set\w+\s*\]\s*=\s*useState[^;]*;")
YEAR_IN_PARAMS = re.compile(
    r"useState\s*(?:<[^>]*>)?\s*\(\s*\{[^{}]*\b(?:fiscal_year|year)\s*:\s*([^,}\n]+)", re.S)
# 同檔內等同於 getFullYear() 的別名（`const currentYear = new Date().getFullYear()`）
YEAR_ALIAS = re.compile(r"\bconst\s+(\w+)\s*=\s*new\s+Date\(\)\.getFullYear\(\)")
# 顯示綁定 —— 篩了卻不顯示＝隱形篩選，比不篩更糟
SELECT_BLOCK = re.compile(r"<Select\b(.*?)/>", re.S)


def _audit_year_default(rel: str, t: str) -> list[tuple[str, str]]:
    """§2.6 ③：有年度篩選的列表頁，預設必須是當年度、且必須顯示出來。

    ⚠️ **這一條的違規形狀是「那個 key 不存在」** —— 而我 2026-08-30 第一版
    判準去找 `year:` 開頭的初始值，於是對「params 裡根本沒有 year」完全是盲的。
    實測後果：`ERPInvoiceSummaryPage`（`{skip:0,limit:20}`）與
    `ERPOperationalListPage`（`fiscal_year` 未設）兩頁的年度 Select
    開場是空的 ⇒ **歷年混算**，而我先前量出來的答案是「0 違規」。
    ⇒ 判準必須以「有沒有年度 setter」為進場條件，再問「預設值在不在」。
    """
    if not YEAR_SETTER.search(t):
        return []                       # 這一頁沒有年度篩選，不適用
    aliases = set(YEAR_ALIAS.findall(t))

    def _is_current_year(expr: str) -> bool:
        return "getFullYear" in expr or any(
            re.search(rf"\b{re.escape(a)}\b", expr) for a in aliases)

    out: list[tuple[str, str]] = []
    st = YEAR_STATE.search(t)
    pm = YEAR_IN_PARAMS.search(t)
    if st and _is_current_year(st.group(0)):
        pass
    elif pm and _is_current_year(pm.group(1)):
        pass
    else:
        out.append((rel, "年度篩選沒有預設當年度 ⇒ 歷年混算（§2.6 ③）"))

    # 顯示綁定：年度 Select 必須有 value/defaultValue
    for m in SELECT_BLOCK.finditer(t):
        blk = m.group(1)
        if not re.search(r"\b(?:fiscal_year|year|yearFilter)\b", blk):
            continue
        if not re.search(r"\b(?:value|defaultValue)=\{", blk):
            out.append((rel, "年度 Select 沒有 value 綁定 ⇒ 篩了卻顯示未選＝隱形篩選"))
    return out


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
    year_reds: list[tuple[str, str]] = []
    year_scanned = 0
    for p in candidates:
        rel = str(p.relative_to(PAGES)).replace("\\", "/")
        t = sources.get(str(p.resolve()), "")
        if "dataIndex" not in t:
            continue
        # §2.6 ③ 的對象是「有年度篩選的列表頁」，與 ① 的「有統計卡」不同集合
        if YEAR_SETTER.search(t):
            year_scanned += 1
            year_reds.extend(_audit_year_default(rel, t))
        if not CARD.search(t):
            continue
        scanned += 1
        if BACKEND_TOTAL.search(t):
            continue
        m = LOCAL_SUM.search(t)
        if m:
            line = t[: m.start()].count("\n") + 1
            reds.append((rel, line, m.group(0).strip()[:60]))

    print("=" * 74)
    print("§2.6 列表頁：① 統計卡分母＝全體　③ 年度篩選預設當年度（weekly 82）")
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

    print(f"  掃描 {year_scanned} 個有年度篩選的業務列表頁（§2.6 ③）")
    if year_scanned == 0:
        print("\n✗ 一個年度篩選都沒掃到 —— 篩選寫法可能變了，③ 的判準已失效")
        return 2
    for rel, why in year_reds:
        print(f"\n  [RED  ] pages/{rel}")
        print(f"           {why}")

    if reds or year_reds:
        if reds:
            print(f"\n⚠️ 這一類的危險不在「現在算錯了」，而在**它會在資料長大時才開始錯**，")
            print("   且畫面上的數字看起來一樣正常。實測案例：發票彙總卡少 74%。")
        if year_reds:
            print("\n⚠️ 年度那一類的危險是**歷年混算**：數字大得莫名其妙，但沒有任何錯誤。")
            print("   而「篩了卻不顯示」更糟 —— 使用者不知道自己看到的是子集。")
        print(f"\nStatus: [RED] ① {len(reds)} 個統計卡用當頁當分母／③ {len(year_reds)} 個年度篩選違規")
        return 1

    # ⚠️ 措辭必須等於判準做了什麼。原本印「統計卡都走後端全量彙總」——
    # 而判準只查「有沒有在分頁陣列上 reduce/for-of」。用 `.map().filter().length`、
    # 用輔助函式、或用本支沒列的變數命名，都會通過而摘要照樣說「都走後端彙總」。
    # CK_AaaP 同日：**分類器正確，而人讀到的摘要說了別的事。**
    print("\n  （沒有偵測到「在分頁陣列上加總」的形態；"
          "本支不保證每張卡都讀後端 totals）")
    print("\nStatus: [GREEN] 統計卡分母正確、年度篩選預設當年度且有顯示")
    return 0


if __name__ == "__main__":
    sys.exit(main())
