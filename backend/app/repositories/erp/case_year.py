# -*- coding: utf-8 -*-
"""案件類統計的年度口徑 —— **唯一定義**。誰要篩年度都從這裡拿條件。

## 現行判準（2026-09-08 owner 裁示）：`erp_quotations.year` 優先，案號年備援

    年度 = year 欄（有值就用它）；year 欄為空 → 案號 `CK{年}_` 的年

## 為什麼 09-05 用案號年、09-08 又改回 year 欄 —— 這兩個裁示不矛盾

09-05 的紀錄寫著「`year` 是報價單**建立那年**，14/277 張與案號年不同 ⇒ 用它篩 2026
會把 2023、2025 的案列進來」。**那個描述當時是對的** —— 但它描述的是**資料髒**，
不是「year 欄的語意錯」。當時的處置是繞過髒欄位（改用案號年頂著）。

09-08 owner 從 `/erp/vendor-accounts` 回報：「115 年度桃園市興辦公共設施…（開口契約）
共 11 協力廠商與費用，為何無對應」。查出來的形狀，**案號年這一邊也會漏**：

    CK2025_01_03_001  案名「115 年度」（＝西元 2026）  year 欄 2026  應付 380 萬
    ⇒ 案號是 2025 年給的號（開口契約跨年度），案件年度卻是 2026
    ⇒ 用案號年篩 2026 ⇒ **整案連同 4 家協力廠商、380 萬應付全部看不到**

⇒ **兩個欄位各漏一半**：case_code 的年是「給號那年」，year 欄本來就該是「案件年度」。
真正的問題從頭到尾都是 **year 欄被寫成建單年**，而不是它的語意不對。

## 所以 09-08 先洗資料，再改判準

逐案用**案名裡的民國年**當第三方佐證（`112年度`／`115年度`；本 repo 09-08 已把
民國年解析收斂到 `app/core/roc_date.py`），13 筆髒 year 全部對得起來：

    CK2025_01_03_001  案名 115 → 2026  = year 欄 2026   ⇒ year 欄是對的，保留
    CK2023_01_01_001  案名 113 → 2024 ≠ year 欄 2026   ⇒ 髒，改成案號年 2023
    …其餘 11 筆同理（含 CK2024_01_01_002 的 year=2025 → 2024）

回填後全庫只剩 `CK2025_01_03_001` 一筆「案號年 ≠ year 欄」，而那一筆是**真的**
跨年度（2025 給號、115 年度執行）—— 也就是 year 欄現在是可信的單一來源。

⚠️ **這個判準的正確性依賴 year 欄保持乾淨**，所以同日加了
`scripts/checks/quotation_year_semantics_audit.py`（weekly 126）：
案名有「NNN 年度」而 year 欄不符即 RED。**沒有那支守門，這裡三個月後會再髒一次。**

權威：`docs/architecture/FIELD_SEMANTICS.md`「年度篩選的口徑」。
"""
from __future__ import annotations

from sqlalchemy import or_

from app.extended.models.erp import ERPQuotation


def quotation_case_year_condition(year: int):
    """回 SQLAlchemy 條件：報價單所屬案件的年度＝year。

    year 欄優先；只有 year 欄是 NULL 時才退回案號年 —— 反過來寫（案號年優先）
    就是 09-05 到 09-08 之間漏掉整個開口契約的原因。
    """
    y = int(year)
    return or_(
        ERPQuotation.year == y,
        # year 欄沒填的舊資料才看案號
        ERPQuotation.year.is_(None) & ERPQuotation.case_code.like(f"CK{y}_%"),
    )
