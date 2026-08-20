# -*- coding: utf-8 -*-
"""年度欄位正規化（統一西元年）。

owner 2026-08-20：「之前有標註統一西元年為主」。

## 為什麼收在收件端

`pm_cases.year` 出現一筆 `115`（`CK2026_PM_01_006`），而同表其他 73 筆是西元 ——
以 2026 篩選看不到那一筆，以 115 篩選也只看得到那一筆。

**那不是使用者填錯**：當時前端 placeholder 寫著「民國年」、表單預設值是
`year: 114`、後端預設是 `dump.get("year") or 114`、schema description 寫
「年度 (民國)」—— 四處都在告訴他填民國，而規範與實際資料是西元。

提示已改，但**只改提示擋不住既有習慣**，而且年度欄位有多個來源
（PM 表單／報價單表單／Excel 匯入／API 直呼）。逐一修等於維護多份判準
（同 2026-08-19 `%3D` 那次的判準：修在收件端）。

## 為什麼可以精確判定

民國 100–199 與西元 1990–2100 **不重疊**，所以不會把西元誤判成民國。
超出兩個區間的值原樣通過 —— 這支不做範圍驗證，那是另一件事。
"""
from __future__ import annotations

from typing import Optional

ROC_MIN, ROC_MAX = 100, 199
ROC_OFFSET = 1911


def normalize_year(v: Optional[int]) -> Optional[int]:
    """民國年轉西元年；已是西元或無法判定則原樣回傳。"""
    if v is None:
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return v
    if ROC_MIN <= n <= ROC_MAX:
        return n + ROC_OFFSET
    return n
