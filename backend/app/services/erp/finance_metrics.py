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


#: 消費端有兩種形狀：查詢裡 join 了報價單（用 `q.id`），或只有一個 bind 參數（`:qid`）。
#: 每個片段都吃 `ref` —— 那是「這一列的報價單 id 怎麼取」的表達式。
def billed_amount(ref: str = "q.id") -> str:
    """已請款合計（該報價單底下所有請款單的請款金額）。"""
    return (
        f"COALESCE((SELECT SUM(b.billing_amount) FROM erp_billings b "
        f"WHERE b.erp_quotation_id = {ref}), 0)"
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
