# -*- coding: utf-8 -*-
"""經費指標的 SQL 片段 —— **唯一實作**。

⭐ owner 2026-09-09：「統計應建構統一服務端，不應依各別頁面各自建構。
請盤點複查整合，避免如此反覆查核每個頁面是否來源或統計基準等問題。」

## 盤點結果（2026-09-09 實測，這支模組存在的理由）

| 指標 | 當時有幾份實作 | 散在幾個檔 |
|---|---|---|
| 承攬金額（議價→契約→報價） | 4 | 3 |
| 已請款合計 | 3 | 3 |
| 已收款合計 | 3 | 3 |
| 應付合計 | 3 | 3 |

而且**已經分歧**：「已收款」三份寫法不同 ——

    financial_summary_repository  SUM(payment_amount) WHERE payment_status IN ('paid','partial')
    quotation_repository          SUM(payment_amount)                    ← 沒有狀態條件
    finance_anomaly               SUM(COALESCE(payment_amount, 0))       ← 沒有狀態條件

⚠️ **實測當下三者give 出同一個數字**（23,072,409）——因為現有 59 筆有金額的請款
狀態剛好全是 `paid`。**那是最危險的狀態**：看起來一致，等到出現第一筆 `partial`
或狀態為空而金額有值的請款，三個畫面就會給出三個數字，而不會有任何一方報錯。

⇒ 這裡的規則是：**要算錢，就從這個模組拿片段，不要自己寫。**

## 為什麼回傳 SQL 片段而不是數值

消費端同時有 raw SQL（`text()`）與 ORM，且多半是「一個大查詢裡的一個欄位」。
回數值會逼每個消費端多打一次資料庫；回片段能直接嵌進既有查詢，遷移成本最低。
代價是呼叫端要傳 alias —— 所以每個函式都有預設值，並在 docstring 寫清楚它假設的 FROM。
"""
from __future__ import annotations

#: 請款「已收」認列哪些狀態。
#:
#: 只認 `paid`／`partial` 是有意的：狀態為 `pending` 而 `payment_amount` 有值，
#: 代表金額填了但還沒確認收到 —— 那不該算進已收。
#: ⚠️ 改這個集合會同時改動每一支統計，這正是把它放在這裡的目的。
RECEIVED_STATUSES = ("paid", "partial")
_RECEIVED_IN = ", ".join("'%s'" % s for s in RECEIVED_STATUSES)


def awarded_amount(c: str = "c", q: str = "q") -> str:
    """承攬金額（含稅）＝**議價 → 契約 → 報價總價**，取第一個非零。

    假設查詢裡有 `contract_projects {c}` 與 `erp_quotations {q}`。

    為什麼是這個順序（`FIELD_SEMANTICS.md`「經費名詞字典」）：
    議價金額是最後談定的數字，沒有議價才看契約，都沒有才退回報價總價。
    `NULLIF(..., 0)` 是必要的 —— 議價欄未填時是 0 而不是 NULL。
    """
    return f"COALESCE(NULLIF({c}.winning_amount, 0), {c}.contract_amount, {q}.total_price, 0)"


def winning_amount_expr(c: str = "c") -> str:
    """議價金額；未填時是 0 而不是 NULL，所以一律 `NULLIF(..., 0)`。只在這裡寫這個式子。"""
    return f"NULLIF({c}.winning_amount, 0)"


def awarded_amount_case_only(c: str = "c") -> str:
    """同 `awarded_amount`，但查詢裡**只有** `contract_projects {c}`（沒 join 報價單）——
    退回報價總價那一層由呼叫端用 `pick_awarded(..., quote_total)` 補上，順序不變。

    2026-09-09 收斂存量三處（請款上限、報價單列表批次、報價單詳情）時量過：
    全庫 281 案裡契約額≠報價總價的只有 1 案（`CK2021_PM_02_003`，L146 匯錯的 351,200 殘留在案件兩張表）
    ⇒ 把「只看議價」改成「議價→契約→報價」不改變任何現有數字。
    """
    return f"COALESCE({winning_amount_expr(c)}, {c}.contract_amount)"


def pick_awarded(winning, contract, quote_total=None):
    """Python 端的同一條規則：議價 → 契約 → 報價總價，取第一個非零；全空回 None。

    給「SQL 只取到 contract_projects 的欄位、報價總價在 ORM 物件上」的呼叫端用；
    不要在呼叫端自己寫 `winning if winning is not None else contract`——那就是第二份實作。
    """
    from decimal import Decimal, InvalidOperation
    for v in (winning, contract, quote_total):
        if v is None:
            continue
        try:
            if Decimal(str(v)) != 0:
                return v
        except (InvalidOperation, ValueError):
            continue
    return None


#: 消費端有兩種形狀：查詢裡 join 了報價單（用 `q.id`），或只有一個 bind 參數（`:qid`）。
#: 每個片段都吃 `ref` —— 那是「這一列的報價單 id 怎麼取」的表達式。
#: 「已請款」認哪些請款單：**有請款日期的**。
#:
#: 2026-09-09 owner：「案件皆請款？這也是大問題」。09-03「成案即應收」讓系統在成案當下自動建一筆
#: 請款單（金額＝承攬金額）當應收佔位，與真的開出去的請款單同表同欄；09-04 的定義把它算進「已請款」
#: ⇒ 每個案成案那一刻就已請款 100%（全庫 96,872,983 裡 31,180,060 是這種佔位，85 筆、全無請款日期）。
#: 09-07 已裁定「沒有請款就沒有請款日期」（佔位留白、人工填報必填）⇒ 請款日期就是「真的請了」的判準。
#: 佔位仍是應收：應收未收＝承攬金額－已收款，不受本條影響。
#: ⚠️ 上限／超支判斷（billing_service 的 110% 檢查、proactive 的請款超支）**要含佔位**，不用本條。
BILLED_CONDITION = "billing_date IS NOT NULL"


def billed_amount(ref: str = "q.id") -> str:
    """已請款合計（該報價單底下**有請款日期**的請款單金額；見 `BILLED_CONDITION`）。"""
    return (
        f"COALESCE((SELECT SUM(b.billing_amount) FROM erp_billings b "
        f"WHERE b.erp_quotation_id = {ref} AND b.{BILLED_CONDITION}), 0)"
    )


def received_amount(ref: str = "q.id") -> str:
    """已收款合計。**只認 `RECEIVED_STATUSES` 的請款單** —— 見該常數的說明。

    ⚠️ 2026-09-09 盤點時這裡有三份實作，狀態條件三種都不同
    （`IN ('paid','partial')`／`= 'paid'`／完全不看狀態）。
    收斂到最嚴謹的那一份，**實測不改變任何現有數字**
    （59 筆有金額的請款狀態全是 `paid`），而未來出現 `partial` 時行為才是對的。
    """
    return (
        f"COALESCE((SELECT SUM(b.payment_amount) FROM erp_billings b "
        f"WHERE b.erp_quotation_id = {ref} AND b.payment_status IN ({_RECEIVED_IN})), 0)"
    )


def payable_amount(ref: str = "q.id") -> str:
    """協力廠商應付合計（掛在該報價單底下的應付，含「指派即應付」自動建的）。"""
    return (
        f"COALESCE((SELECT SUM(p.payable_amount) FROM erp_vendor_payables p "
        f"WHERE p.erp_quotation_id = {ref}), 0)"
    )


def paid_amount(ref: str = "q.id") -> str:
    """協力廠商已付合計。狀態條件與 `received_amount` 同一組（實測同樣不改變現有數字）。"""
    return (
        f"COALESCE((SELECT SUM(p.paid_amount) FROM erp_vendor_payables p "
        f"WHERE p.erp_quotation_id = {ref} AND p.payment_status IN ({_RECEIVED_IN})), 0)"
    )


def case_year_condition(year: int, c: str = "c", q: str = "q", param: str = "yr") -> str:
    """案件年度條件。**`year` 欄優先，案號年只是後備。**

    2026-09-08 裁定的口徑（`app/repositories/erp/case_year.py` 有完整脈絡）：
    案號的年是「給號那年」，`year` 欄才是「案件年度」。
    開口契約會跨年度 —— `CK2025_01_03_001` 是 2025 年給的號、2026 年度執行，
    用案號年篩 2026 就會整案連同 1,693 萬承攬額消失。

    ⚠️ 2026-09-09 owner 從財務儀表板回報的「各數據不一致」就是這一條沒有統一：
    上方 KPI 用 `year` 欄算出 108,108,873，下方類別分解用案號年算出 91,173,873。

    回傳的片段需要 `:{param}_i`（整數年）與 `:{param}`（`CK{年}_%`）兩個 bind 參數。
    """
    return f"({c}.year = :{param}_i OR ({c}.year IS NULL AND {q}.case_code LIKE :{param}))"


def case_year_params(year: int, param: str = "yr") -> dict:
    """`case_year_condition` 需要的 bind 參數。兩者必須一起用。"""
    return {f"{param}_i": int(year), param: f"CK{int(year)}_%"}

#: 案號的類別碼（`01` 委辦招標／`02` 承攬報價）。新制 `CK2026_PM_02_001` 在模組段之後，
#: 舊制 `CK2025_01_01_001` 在年度之後。與 `services/erp/quote_kind.category_of` 同一條規則。
_CAT_RE = "^CK" + chr(92) + "d{4}_(?:PM_|GN_|FN_|DP_)?(" + chr(92) + "d{2})_"


def case_category_expr(case_code_col):
    """回 SQLAlchemy 表達式：從案號欄取出類別碼。

    2026-09-09 owner「篩選機制模組化」：帳款兩頁此前**沒有**計畫類別條件，
    而財務摘要 repository 自己寫了一份 `substring(... from '^CK...')`（text 版）。
    ORM 版放這裡，讓帳款頁與其他 ORM 查詢共用；text 版那一份是存量（基線內）。

    用法：`query.where(case_category_expr(ERPQuotation.case_code) == "02")`
    """
    from sqlalchemy import func

    return func.substring(case_code_col, _CAT_RE)


# ── 分組（GROUP BY）版：查詢已經 JOIN 了請款／應付表，要的是聚合表達式不是子查詢 ──
# 2026-09-09：基線裡 4 處存量正是這個形狀（財務摘要 pay_rows、金流異常判準的逐案聚合）。
# 口徑與上面的子查詢版**必須一致**（同一組 RECEIVED_STATUSES），差別只在形狀。
def billed_amount_agg(b: str = "b") -> str:
    """已請款聚合，查詢已 JOIN `erp_billings {b}`；只認有請款日期的（`BILLED_CONDITION`）。"""
    return f"COALESCE(SUM(CASE WHEN {b}.{BILLED_CONDITION} THEN {b}.billing_amount END), 0)"


def received_amount_agg(b: str = "b") -> str:
    """已收款聚合，**只認 RECEIVED_STATUSES** —— 與 `received_amount` 同口徑。"""
    return f"COALESCE(SUM(CASE WHEN {b}.payment_status IN ({_RECEIVED_IN}) THEN {b}.payment_amount END), 0)"


def payable_amount_agg(p: str = "p") -> str:
    """`SUM(p.payable_amount)`，查詢已 JOIN `erp_vendor_payables {p}`。"""
    return f"COALESCE(SUM({p}.payable_amount), 0)"


def paid_amount_agg(p: str = "p") -> str:
    """已付聚合，狀態條件與 `paid_amount` 同一組。"""
    return f"COALESCE(SUM(CASE WHEN {p}.payment_status IN ({_RECEIVED_IN}) THEN {p}.paid_amount END), 0)"


# ---------------------------------------------------------------------------
# SQLAlchemy Core 版（給用 `select(func.sum(...))` 的消費端）。
# 2026-09-09 才發現 weekly 132 的字樣判準只認 SQL 文字，`func.sum(ERPBilling.billing_amount)`
# 這種寫法它看不見 —— 七處存量就這樣躲了一天。口徑與上面的 SQL 片段**逐字相同**，改一邊必改另一邊
# （`test_finance_metrics.py` 鎖兩邊同值）。
# ---------------------------------------------------------------------------
def billed_amount_col(B):
    """`B`＝`ERPBilling` model。已請款＝有請款日期的請款單金額。"""
    from sqlalchemy import case, func
    return func.coalesce(func.sum(case((B.billing_date.isnot(None), B.billing_amount), else_=0)), 0)


def received_amount_col(B):
    """已收款＝`RECEIVED_STATUSES` 的請款單的收款金額。"""
    from sqlalchemy import case, func
    return func.coalesce(func.sum(case((B.payment_status.in_(RECEIVED_STATUSES), B.payment_amount), else_=0)), 0)


def payable_amount_col(P):
    """`P`＝`ERPVendorPayable`。應付合計。"""
    from sqlalchemy import func
    return func.coalesce(func.sum(P.payable_amount), 0)


def paid_amount_col(P):
    """已付＝`RECEIVED_STATUSES` 的應付的已付金額（與 `paid_amount` 同口徑）。"""
    from sqlalchemy import case, func
    return func.coalesce(func.sum(case((P.payment_status.in_(RECEIVED_STATUSES), P.paid_amount), else_=0)), 0)


def awarded_amount_col(C, Q):
    """承攬金額（議價→契約→報價總價），`C`＝`ContractProject`、`Q`＝`ERPQuotation`（查詢已 outer join）。"""
    from sqlalchemy import func
    return func.coalesce(func.nullif(C.winning_amount, 0), C.contract_amount, Q.total_price, 0)
