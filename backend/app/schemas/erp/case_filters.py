# -*- coding: utf-8 -*-
"""案件類列表的共同篩選條件 —— **單一定義**（owner 2026-09-09「整合篩選條件，請擴大各頁面整合評估」）。

擴大盤點（全部列表頁）後，案件類有**四份**各自定義的篩選 schema：

| schema | 年度 | 類別 | 承辦 | 狀態 | 委託單位 | 異常 | 關鍵字欄名 |
|---|---|---|---|---|---|---|---|
| `ProjectListQuery`（承攬案） | ✓ | ✓ | ✓ | ✓ | — | — | `search` |
| `PMCaseListRequest`（PM 案） | ✓ | ✓ | ✓ | ✓ | ✓ | — | `search`（繼承） |
| `ERPQuotationListRequest`（報價單） | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `search`（繼承） |
| `CaseListFilters`（帳款兩頁，本檔） | ✓ | ✓ | ✓ | — | — | — | `keyword` |

同一個概念、四份宣告、兩個關鍵字欄名。**這裡是那四份要收斂到的家**；
遷移順序與風險見 `docs/architecture/FILTER_MODULARIZATION_20260909.md` §七。
對應統計那一側的 `services/stats/case_scope.CaseStatsScope`——篩選是範圍的 UI 面，維度必須一致。
"""
from typing import Optional

from pydantic import BaseModel, Field

class CaseListFilters(BaseModel):
    """案件類列表的**共同篩選條件 —— 單一定義**。

    ⭐ owner 2026-09-09：「請統整評估篩選機制模組化，與統計相同概念避免頁面重複建構，
    也避免異值同工，另減少 A 頁面有某查詢條件但 B 頁面卻無等操作不一致，如專案財務三個分頁」。

    盤點當時（三個財務分頁）：

    | 條件 | 報價單頁 | 委託帳款 | 協力帳款 |
    |---|---|---|---|
    | 年度 | 表頭漏斗 | 下拉 | 下拉 |
    | 計畫類別 | 有 | **無** | **無** |
    | 承辦同仁 | 有 | 有 | 有 |
    | 委託單位 | 有 | （本頁即以它分組） | **無** |
    | 金流異常 | 有 | **無** | **無** |
    | 關鍵字 | 案號／案名 | 單位名／統編（**沒有案名**） | 廠商名／統編（**沒有案名**） |

    而上面兩個 Request 的 `year／keyword／staff_user_id／skip／limit` **逐字重複兩份**，
    連註解都是複製的 —— 那就是篩選層的異值同工。

    對應 `services/stats/case_scope.CaseStatsScope`（統計的「範圍」）：
    **篩選是範圍的 UI 面，兩者的維度必須一樣**，否則列表能篩的統計卡不會跟著篩。
    """
    year: Optional[int] = Field(None, description="案件年度（西元，§2.5）")
    # 2026-09-09：三頁裡只有報價單頁有這個條件，帳款兩頁沒有 ⇒ 補齊
    category: Optional[str] = Field(None, pattern=r"^(01|02)$", description="計畫類別：01 委辦招標／02 承攬報價")
    keyword: Optional[str] = Field(None, description="關鍵字：名稱／統編／**案名**（09-09 起三頁一致涵蓋案名）")
    # 2026-09-07 owner：「也需對應承辦同仁呈現對應資訊，避免資訊爆炸」。
    # 選了承辦就在**案號層**限縮：案件數、金額與統計卡全部跟著走。
    # 這是使用者自己選的篩選，不是 RLS——可見範圍仍由伺服器依身分決定。
    staff_user_id: Optional[int] = Field(None, description="只看這位承辦同仁名下的案")
    skip: int = 0
    # 2026-09-04 owner「/erp/client-accounts 表格無法查詢」：委託單位 186 家、預設 50 ⇒ 頁面永遠只有 50 家。
    # 彙總是每家一列，上限放到 1000（weekly 95 家族：上限壞在資料長過它的那天——頁面另有截斷警示）。
    limit: int = Field(50, ge=1, le=1000)
