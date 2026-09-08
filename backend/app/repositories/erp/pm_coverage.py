# -*- coding: utf-8 -*-
"""「這個承攬案是不是已經被某個 PM 案涵蓋」—— **唯一定義**。

## 為什麼要有這一支（2026-09-08）

owner 從 `/erp/client-accounts/80?year=2026` 回報：同一個案名出現兩列 ——

    CK2026_PM_01_006  南投縣政府115年度委外辦理圖根點清理及補建新建作業  合約額 0
    CK2026_GN_01_001  南投縣政府115年度委外辦理圖根點清理及補建新建作業  合約額 1,000,000

實查是**同一件工作**：`pm_cases` 243 與 `contract_projects` 190 共用
`project_code = CK2026_01_01_008`，只是兩張表的 `case_code` 不同
（一個 PM 制、一個 GN 制）。

委託單位帳款的「腿 2」本來就有去重（只收 PM 沒涵蓋到的承攬案），
但那條規則**只比對 `case_code`**：

    ~ContractProject.case_code.in_(select(PMCase.case_code))

⇒ `CK2026_GN_01_001` 不在 PM 的 case_code 集合裡 ⇒ 被當成另一個案收進來。

**這是「兩條綁法只認其一」家族的又一處**（同 `assignment_two_binding_paths`
的 `case_code` / `project_id` 兩條互斥綁法）。PM 與承攬案有兩種連法：

| 連法 | 什麼時候成立 |
|---|---|
| `case_code` 相同 | PM 成案時沿用同一個案號（「去 `_PM_`」那條路徑） |
| `project_code` 相同 | PM 成案拿到正式編號，而承攬案自己另有 case_code（GN 制標案） |

只認第一條，第二條的案就會**在明細頁多出一列**，而那一列的合約金額是 0
（金額查得到的是另一列）—— 看起來像「重複案件」，實際是同一案被切成兩半。

## 為什麼是修判準不是修資料

`CK2026_GN_01_001` 有 1 張報價單與 1 筆指派掛在上面，`CK2026_PM_01_006` 沒有
⇒ 改案號要連動那些引用，風險遠高於修判準；而且判準修好可以防未來復發。
全庫實測此型只有這 1 筆，但它會隨每一次「PM 案與 GN 標案指向同一件工作」再長出來。

## 三份宣告收斂成一份

此前這條排除規則有**三份**：`client_receivable_repository` 的列表腿 2 與明細腿 2、
`case_profile.py` 的手寫 SQL（註解自稱「與 client_receivable_repository 同一條排除規則」）。
本檔是唯一定義；手寫 SQL 版沒辦法 import，用下方 `PM_COVERED_SQL` 讓兩邊至少共用同一段文字。
"""
from __future__ import annotations

from sqlalchemy import and_, or_, select

from app.extended.models.core import ContractProject
from app.extended.models.pm import PMCase


def contract_covered_by_pm():
    """SQLAlchemy 條件：這個 `ContractProject` 已被某個 PM 案涵蓋。

    用法是取反 —— `~contract_covered_by_pm()` ＝「只收 PM 沒涵蓋到的承攬案」。
    """
    by_case = ContractProject.case_code.in_(
        select(PMCase.case_code).where(
            PMCase.client_vendor_id.isnot(None),
            PMCase.case_code.isnot(None),
        )
    )
    # 2026-09-08 新增的第二條：PM 成案拿到 project_code，而承攬案另有自己的 case_code
    by_project = and_(
        ContractProject.project_code.isnot(None),
        ContractProject.project_code.in_(
            select(PMCase.project_code).where(
                PMCase.client_vendor_id.isnot(None),
                PMCase.project_code.isnot(None),
            )
        ),
    )
    return or_(by_case, by_project)


#: 手寫 SQL 版（`case_profile.py` 用）—— 與上面的 `contract_covered_by_pm` 是同一條規則。
#: ⚠️ 改上面就要改這裡；SQL 端無法 import，這是刻意留下的兩處，不是漏收斂。
PM_COVERED_SQL = """(
           cp.case_code IN (SELECT case_code FROM pm_cases
                             WHERE client_vendor_id IS NOT NULL AND case_code IS NOT NULL)
        OR (cp.project_code IS NOT NULL
            AND cp.project_code IN (SELECT project_code FROM pm_cases
                                     WHERE client_vendor_id IS NOT NULL AND project_code IS NOT NULL))
       )"""
