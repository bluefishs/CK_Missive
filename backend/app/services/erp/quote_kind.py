# -*- coding: utf-8 -*-
"""報價單種類（`erp_quotations.quote_kind`）的推導 —— 單一來源。

2026-09-02 晚，owner 問「全系統 250 張報價單裡 01 有 25 張，為何報價單有 01 委辦招標？」
答案是 `erp_quotations` 裝了三種東西，而表上沒有欄位說它是哪一種：

| quote_kind        | 是什麼                                   | 誰建的                                  |
|-------------------|------------------------------------------|-----------------------------------------|
| ``tender``        | 01 委辦招標的投標報價（draft）           | 標案建案（owner 08-17：報價在投標前）   |
| ``contract``      | 02 承攬報價 —— 人工報價、XLS 匯入        | /pm/cases 新增報價、彙整表匯入          |
| ``finance_anchor``| 成案時自動建的 0 元錨點，只為請款有地方掛 | ``promote_to_project``／04-04 一次性批次 |

owner 的「115 報價單彙整總表」**只對 ``contract``**；01 一律不在刪除／合併範圍。
先前這條規則只能靠 case_code 段落＋人的記憶，現在可以寫成查詢條件。

寫入端三條路徑各自帶明確值（tender／contract／finance_anchor），這裡的推導只給
**沒帶值的路徑**（``quotation_service.create``）與 migration 回填用。
規則刻意只看 case_code，不看金額：0 元的承攬報價是存在的（草稿），不能因為 0 元就判錨點。
"""
from __future__ import annotations

import re
from typing import Optional

TENDER = "tender"
CONTRACT = "contract"
FINANCE_ANCHOR = "finance_anchor"
KINDS = (TENDER, CONTRACT, FINANCE_ANCHOR)

# 新制 CK2026_PM_02_001 / CK2026_GN_02_001：模組後那一段是類別
_NEW = re.compile(r"^CK\d{4}_(PM|GN|FN|DP)_(0[12])_")
# 舊制 CK2025_01_01_001：第一段就是類別（01 委辦招標／02 承攬報價／03 其他）
_OLD = re.compile(r"^CK\d{4}_(0[123])_\d{2}_")


def category_of(case_code: Optional[str]) -> Optional[str]:
    """從案號取出類別碼（``"01"``／``"02"``／``"03"``），認不出回 None。"""
    if not case_code:
        return None
    m = _NEW.match(case_code) or _OLD.match(case_code)
    return m.group(2) if m and m.re is _NEW else (m.group(1) if m else None)


def infer_quote_kind(case_code: Optional[str], *, auto_created: bool = False) -> Optional[str]:
    """由案號推導種類。``auto_created=True``（成案自動建）一律是錨點。"""
    if auto_created:
        return FINANCE_ANCHOR
    cat = category_of(case_code)
    if cat == "01":
        return TENDER
    if cat == "02":
        return CONTRACT
    return None


#: migration 與一次性回填用的 SQL 片段 —— 與上面 Python 規則等價，改一邊要改另一邊
#:（``test_case_field_sync_and_quote_kind`` 用 8 組已知案號同時打兩邊，對不上就紅）。
BACKFILL_SQL = """
UPDATE erp_quotations SET quote_kind = CASE
    WHEN notes LIKE '隨承攬案件%自動建立%' THEN 'finance_anchor'
    WHEN case_code ~ '^CK\\d{4}_(PM|GN|FN|DP)_01_' OR case_code ~ '^CK\\d{4}_01_\\d{2}_' THEN 'tender'
    WHEN case_code ~ '^CK\\d{4}_(PM|GN|FN|DP)_02_' OR case_code ~ '^CK\\d{4}_02_\\d{2}_' THEN 'contract'
    ELSE NULL END
WHERE quote_kind IS NULL
"""
