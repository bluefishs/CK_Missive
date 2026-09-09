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
from typing import Any, Callable, Optional


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
    #: 角色決定的可見範圍（RLS）。承攬案有（`RLSFilter.apply_project_rls`），PM 案目前沒有。
    #: 簽名：`rls(query, current_user) -> query`。沒給就是「這個實體不套 RLS」。
    rls: Optional[Callable[[Any, Any], Any]] = None


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

    async def resolve_case_codes(self, db) -> Optional[set]:
        """身分範圍展開成 case_code 集合；沒有指定承辦時回 None（不限縮）。

        走 `case_codes_of_user`，那一支**會展開身分合併的 alias 群** ——
        2026-09-09「顯示 (3) 卻 0 家」就是某個消費端只認 canonical id。這裡不另寫一份。
        """
        if self.staff_user_id is None:
            return None
        from app.repositories.erp.case_staff import case_codes_of_user

        return await case_codes_of_user(db, self.staff_user_id) or {"__none__"}

    def apply_sync(self, query, cols: CaseColumns, *, case_codes: Optional[set] = None,
                   current_user=None, with_status: bool = False):
        """把範圍條件套上查詢（**純 SQL 組裝，不打 DB**）。

        消費端多半在一個 async 方法裡對三、四個子查詢各套一次範圍 ——
        承辦的案號集合先用 `resolve_case_codes` 查一次，再拿這支同步套用多次。

        `with_status=False` 是預設：**狀態通常不該套在計數上**——統計卡是分母，
        點了某張狀態卡其他卡的數字不能跟著歸零（規範 §2.6 ②）。

        `current_user` 給了且 `cols.rls` 有定義 ⇒ 先套角色可見範圍（RLS），再套承辦篩選；
        後者只能在前者**之內**縮小（覆蓋就等於前端傳什麼給什麼，RLS 形同虛設）。
        """
        if current_user is not None and cols.rls is not None:
            query = cols.rls(query, current_user)
        if self.year is not None:
            query = query.where(cols.year == self.year)
        if self.category:
            query = query.where(cols.category == self.category)
        if with_status and self.status:
            query = query.where(cols.status == self.status)
        if case_codes is not None:
            query = query.where(cols.case_code.in_(case_codes))
        return query

    async def apply(self, db, query, cols: CaseColumns, *, with_status: bool = False, current_user=None):
        """`resolve_case_codes` ＋ `apply_sync` 的合成，給只套一次的消費端用。"""
        codes = await self.resolve_case_codes(db)
        return self.apply_sync(query, cols, case_codes=codes, current_user=current_user, with_status=with_status)


def _contract_rls(query, current_user):
    from app.core.rls_filter import RLSFilter
    from app.extended.models import ContractProject

    uid, is_admin, is_su = RLSFilter.get_user_rls_flags(current_user)
    return RLSFilter.apply_project_rls(query, ContractProject, uid, is_admin, is_su)


def contract_project_columns() -> CaseColumns:
    """承攬案（`contract_projects`）的欄位對映。延遲 import 避免模型層循環引用。"""
    from app.extended.models import ContractProject as C

    return CaseColumns(year=C.year, status=C.status, category=C.category, case_code=C.case_code, rls=_contract_rls)


def pm_case_columns() -> CaseColumns:
    """PM 案（`pm_cases`）的欄位對映。PM 沒有 RLS，可見範圍只由使用者自選的承辦篩選決定。"""
    from app.extended.models import PMCase as P

    return CaseColumns(year=P.year, status=P.status, category=P.category, case_code=P.case_code)
