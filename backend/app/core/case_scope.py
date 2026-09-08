# -*- coding: utf-8 -*-
"""案件範圍守衛 —— 「你只能動自己承辦的案」。

## 為什麼有這一支（2026-09-08 owner）

owner：「`projects:write` 重點要對能對應承辦同仁案件，以利管控」。

背景是費用核銷的四支操作端點（`approve`／`batch-approve`／`reject`／`delete`）
掛著 `require_permission("projects:write")`，而實查 **`projects:write` 這個權限碼
在全系統不存在** —— `role_permissions` 0 筆、12 個在職使用者 0 人、
前端權限目錄也沒有 ⇒ 那四支對所有非 superuser **永遠 403**。

而 `expense_approval.py` 的註解還寫著「每一層都只要 `projects:write`
（11 個在職帳號都有）」。**兩份宣告，一份改了另一份沒改**，
失效方向是安靜的 403，沒有人會收到通知。

## 為什麼不是「換一個現成的碼就好」

最接近的 `projects:edit` 有 **11/12 位在職使用者持有（含全部 staff）**
⇒ 換上去等於全開，那不叫管控。

owner 要的是**範圍**不是**等級**：能不能核銷這一筆，取決於
「這筆核銷所屬的案子是不是我承辦的」，而不是「我的職級夠不夠高」。

## 判準

| 身分 | 範圍 |
|---|---|
| superuser | 全部（既有慣例：`is_superuser_user` 直通） |
| admin／exec | 全部 —— 這兩個角色本來就是全公司視角（同 `/erp/client-accounts`／`/erp/vendor-accounts` 2026-08-31 的裁示） |
| 其他（staff／finance／ops…） | **只有自己承辦的案**（`RLSFilter.get_user_accessible_case_codes`） |

`case_code` 為空的紀錄：非全公司視角者一律拒絕 —— 歸屬不明的東西不該讓
「只能動自己案子」的人動，而且那本身就是一個要補的填報缺口。

⚠️ 範圍來源**沿用既有的 `RLSFilter`**，不自己寫一份 assignment 查詢：
它已經處理了 alias group（分身帳號）與**兩條互斥的綁法**
（`case_code`／`project_id`），而本 repo 為「只認其中一條」的實作付過八次學費
（`assignment_two_binding_paths`）。weekly 93 也在盯「新腳本不得自己重造」。
"""
from __future__ import annotations

from typing import Iterable, Optional


from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import is_superuser_user

#: 全公司視角的角色 —— 與委託單位／協力廠商帳款兩頁同一組判準。
_COMPANY_WIDE_ROLES = {"admin", "exec", "superuser"}


def has_company_wide_scope(user) -> bool:
    """這個人是不是全公司視角（不受案件範圍限制）。"""
    if user is None:
        return False
    if is_superuser_user(user):
        return True
    return str(getattr(user, "role", "") or "").lower() in _COMPANY_WIDE_ROLES


async def accessible_case_codes(db: AsyncSession, user_id: int) -> set[str]:
    """該使用者（含分身）承辦的案號集合。"""
    from app.core.rls_filter import RLSFilter

    rows = (await db.execute(RLSFilter.get_user_accessible_case_codes(user_id))).all()
    return {r[0] for r in rows if r[0]}


async def assert_case_scope(
    db: AsyncSession,
    user,
    case_codes: Optional[Iterable[Optional[str]]],
    action: str = "操作",
) -> None:
    """不在範圍內就丟 ForbiddenException（403），訊息要說得出「為什麼」。

    `case_codes` 傳一組是為了批次操作 —— 只要有一筆不在範圍內就整批擋，
    否則批次會變成「繞過單筆守衛」的後門（本 repo 對『第二條寫入路徑』
    的教訓已經夠多了）。
    """
    from app.core.exceptions import ForbiddenException

    if has_company_wide_scope(user):
        return

    codes = [c for c in (case_codes or [])]
    if not codes:
        return

    mine = await accessible_case_codes(db, getattr(user, "id", 0))

    missing = [c for c in codes if not c]
    if missing:
        raise ForbiddenException(
            f"這筆紀錄沒有案號，無法判斷是不是你承辦的案 —— 不開放{action}。"
            "請先補上案號（或由管理者處理）。"
        )
    outside = sorted({c for c in codes if c not in mine})
    if outside:
        raise ForbiddenException(
            f"只能{action}自己承辦的案件。{'、'.join(outside[:3])}"
            f"{f' 等 {len(outside)} 案' if len(outside) > 3 else ''}不在你的承辦範圍內。"
        )
