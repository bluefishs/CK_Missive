# -*- coding: utf-8 -*-
"""案件統計的**範圍**唯一定義 —— owner 2026-09-09「案件與經費等統計請整合建構中心服務」。

## 為什麼需要它

承攬案（`contract_projects`）與 PM 案（`pm_cases`）的統計是**兩份平行實作**：
形狀完全一樣（一個範圍條件套上三、四個子查詢），而各自寫在自己的 repository 裡。

2026-09-09 一天內就修了兩次同一種缺陷：
`/contract-cases` 與 `/pm/cases` 的統計卡都沒有跟上列表的身分範圍，
而兩次是分開發現、分開修的 —— **因為它們是兩份程式碼。**

⇒ 範圍的語意（年度／身分／類別／狀態）收成一份，兩個實體用**欄位對映**接上去。

## 統計 ＝ 範圍 × 指標

指標在 `app.services.stats.finance`，範圍在這裡。
過去兩者都散在各頁面自己的查詢裡，於是「同一個名詞、不同的算法」到處都是。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class CaseColumns:
    """一個案件實體要參與統計時，必須指出它的四個欄位。

    刻意用明確的欄位物件而不是字串：欄位改名時 tsc 等價的保護（Python 端是 import
    時就會爆）比字串好 —— 字串打錯只會安靜地少一個條件。
    """

    year: Any
    status: Any
    category: Any
    case_code: Any


@dataclass
class CaseStatsScope:
    """一組統計要看的範圍。**所有維度都是可選的，沒給就是不限縮。**

    ⚠️ 身分（`staff_user_id`）也是範圍的一種。
    2026-09-09 owner 兩次回報「列表篩了而統計卡沒篩」，根因就是這一點沒有被當成
    範圍的一部分 —— 年度與類別大家都記得傳，身分卻常常漏掉。
    把它放進同一個 dataclass，漏掉就會在呼叫端看得出來。
    """

    year: Optional[int] = None
    staff_user_id: Optional[int] = None
    category: Optional[str] = None
    status: Optional[str] = None

    async def case_codes(self, db) -> Optional[set]:
        """身分範圍展開成 case_code 集合；沒有指定身分時回 None（不限縮）。

        ⚠️ 走 `case_codes_of_user`，那一支**會展開身分合併的 alias 群** ——
        2026-09-09 owner 從 `/erp/vendor-accounts` 回報的「顯示 (3) 卻 0 家」
        就是因為某個消費端只認 canonical id。這裡不另寫一份。
        """
        if self.staff_user_id is None:
            return None
        from app.repositories.erp.case_staff import case_codes_of_user

        return await case_codes_of_user(db, self.staff_user_id) or {"__none__"}

    async def apply(self, db, query, cols: CaseColumns, *, with_status: bool = False):
        """把範圍條件套上查詢。

        `with_status=False` 是預設，因為**狀態通常不該套在計數上** ——
        統計卡是分母，點了某張狀態卡其他卡的數字不能跟著歸零（規範 §2.6 ②）。
        只有金額類的查詢才把狀態帶進去。
        """
        if self.year is not None:
            query = query.where(cols.year == self.year)
        if self.category:
            query = query.where(cols.category == self.category)
        if with_status and self.status:
            query = query.where(cols.status == self.status)
        codes = await self.case_codes(db)
        if codes is not None:
            query = query.where(cols.case_code.in_(codes))
        return query
