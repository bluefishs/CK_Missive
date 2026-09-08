# -*- coding: utf-8 -*-
"""案件 → 承辦同仁（唯一實作）。

## 為什麼要有這一支

「這個案的承辦是誰」在本 repo 曾經有**八份各自演化的實作**，而且其中一半是錯的
（`assignment_two_binding_paths`）。`project_user_assignments` 有兩條**互斥**的綁法：

| 綁法 | 什麼時候寫的 |
|---|---|
| `case_code` | 邀標／報價階段——還沒成案，沒有 `project_id` 可寫 |
| `project_id` | 成案之後從承攬案件那一側指派 |

只認其中一條的查詢，會**安靜地少掉另一半的承辦**（owner 2026-08-31 從
`/erp/quotations/541` 回報「沒有承辦」，實查是那筆指派只綁 `project_id`）。

⇒ 這支是那個 UNION 的**唯一家**。要問承辦的人一律 import 它，不要再抄一次 SQL。
`quotation_service._get_staff_names_batch` 已改為委派本支（原文與教訓留在該處註解）。

ADR-0025：以 canonical 人為準——分身帳號不得顯示成兩個人。
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

#: 兩條綁法的 UNION。`:cs` ＝ case_code 陣列。
_ASSIGNMENTS_BY_CASE = """
    SELECT k.case_code AS case_code,
           u.id        AS user_id,
           COALESCE(u.full_name, u.username) AS name
      FROM (
            -- 綁 case_code 的指派（邀標／報價階段）
            SELECT pa.case_code, pa.user_id, pa.status
              FROM project_user_assignments pa
             WHERE pa.case_code = ANY(:cs)
            UNION ALL
            -- 綁 project_id 的指派（成案之後）—— 反查該專案的 case_code
            SELECT cp.case_code, pa2.user_id, pa2.status
              FROM project_user_assignments pa2
              JOIN contract_projects cp ON cp.id = pa2.project_id
             WHERE pa2.project_id IS NOT NULL
               AND cp.case_code = ANY(:cs)
           ) k
      LEFT JOIN users au ON au.id = k.user_id
      LEFT JOIN users u  ON u.id = COALESCE(au.canonical_user_id, au.id)
     WHERE COALESCE(k.status, 'active') <> 'inactive'
       AND u.id IS NOT NULL
       -- ⭐ 2026-09-08 owner：「承辦同仁案件對應問題，/erp/vendor-accounts、
       -- /erp/client-accounts 前端仍未排除」。實查下拉與欄位裡出現兩個**系統帳號**：
       --   · `SuperUser`（id 1, admin, **已停用**）—— 佔位帳號，卻掛著 1 筆指派
       --   · `王駿穠(fly)`（superuser）—— 見下方 canonical 的說明
       -- 停用帳號不該出現在「承辦同仁」：它既不能登入、也不會有人再指派給它，
       -- 而列在下拉裡選下去只會得到一片空白（那正是 assignable_staff 檔頭
       -- 已經寫過的理由，只是當時沒把停用這一種算進去）。
       AND COALESCE(u.is_active, FALSE) IS TRUE
"""


async def staff_by_case_code(
    db: AsyncSession, case_codes: Iterable[str]
) -> dict[str, list[dict[str, Any]]]:
    """`{case_code: [{"user_id": .., "name": ..}, ...]}`；沒有指派的案不出現在結果裡。"""
    codes = sorted({c for c in case_codes if c})
    if not codes:
        return {}
    rows = (await db.execute(
        text(f"SELECT DISTINCT case_code, user_id, name FROM ({_ASSIGNMENTS_BY_CASE}) t"),
        {"cs": codes},
    )).all()
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        # 位置取值：SELECT 的欄序就寫在上一行，而具名取值在單元測試把 execute
        # mock 成回傳純 tuple 時會 AttributeError —— 那是測試該不該改的問題，
        # 但這裡沒有必要為了寫法漂亮讓一支既有測試變成假紅。
        code, uid, name = r[0], r[1], r[2]
        out.setdefault(code, []).append({"user_id": uid, "name": name})
    for v in out.values():
        v.sort(key=lambda x: x["name"] or "")
    return out


async def staff_names_by_case_code(db: AsyncSession, case_codes: Iterable[str]) -> dict[str, str]:
    """`{case_code: "甲、乙"}`——給只要顯示一行字的呼叫端（報價單列表就是）。"""
    return {
        code: "、".join(s["name"] for s in staff if s["name"])
        for code, staff in (await staff_by_case_code(db, case_codes)).items()
    }


#: 一個人的**所有帳號**（身分合併後的同一人）。
#:
#: ⭐ 2026-09-09 owner 從 `/erp/vendor-accounts` 回報：「以王駿穠登入，篩選李昭德
#: 顯示（3）且經費為零」。實查：
#:
#:     id=11 staff_李昭德   canonical_user_id=19  **已停用**  ← CK2025_01_03_001（380 萬）掛在這裡
#:     id=19 luke19630612  canonical=None        在用       ← 下拉顯示的就是這個 id
#:
#: 下拉（`assignable_staff`）**有**展開 alias（`COALESCE(au.canonical_user_id, au.id)`）
#: ⇒ 算出 3 個案；而 `case_codes_of_user` **沒有**展開 ⇒ 只拿到 2 個
#: ⇒ 選了 2026 年度後一個都不剩，畫面顯示「共 0 家、經費 0」。
#:
#: **同一個檔案裡兩支函式對「這個人是誰」用了兩份定義**，而兩個數字各自看都對。
#: 這是 ADR-0025 身分合併家族的又一處：合併寫進去了，消費端沒有跟著展開。
_ALIAS_GROUP = """
    SELECT u.id FROM users u
     WHERE u.id = COALESCE((SELECT canonical_user_id FROM users WHERE id = :uid), :uid)
        OR u.canonical_user_id = COALESCE((SELECT canonical_user_id FROM users WHERE id = :uid), :uid)
"""


async def case_codes_of_user(db: AsyncSession, user_id: int) -> set[str]:
    """某個人被指派到的所有 case_code（兩條綁法都算，**alias 帳號一併展開**）。

    給「只看我的」這種**使用者自己選的**篩選用。
    ⚠️ 這不是 RLS —— 可見範圍由伺服器依身分決定（見 `_quotation_scope`），
    本函式只回答「這個人的案有哪些」，呼叫端要自己決定拿它做什麼。

    ⚠️ **`:uid` 可以是 alias 也可以是 canonical**，兩邊都要得到同一個答案 ——
    停用的舊帳號上仍掛著真實的指派（見 `_ALIAS_GROUP` 的說明），
    只認其中一個 id 就會讓那些案憑空消失，而畫面上只顯示「沒有資料」。
    """
    rows = (await db.execute(text(f"""
        SELECT DISTINCT pa.case_code
          FROM project_user_assignments pa
         WHERE pa.user_id IN ({_ALIAS_GROUP}) AND pa.case_code IS NOT NULL
           AND COALESCE(pa.status, 'active') <> 'inactive'
        UNION
        SELECT DISTINCT cp.case_code
          FROM project_user_assignments pa2
          JOIN contract_projects cp ON cp.id = pa2.project_id
         WHERE pa2.user_id IN ({_ALIAS_GROUP}) AND cp.case_code IS NOT NULL
           AND COALESCE(pa2.status, 'active') <> 'inactive'
    """), {"uid": int(user_id)})).all()
    return {r[0] for r in rows if r[0]}


async def assignable_staff(db: AsyncSession, accessible_case_codes=None) -> list[dict[str, Any]]:
    """承辦同仁下拉的選項＝**實際有被指派過的人**，不是全體使用者。

    為什麼不列全體：下拉列出沒有任何案的人，選了就是一片空白，
    使用者會以為是系統壞了。選項只給選了有東西的。

    ⭐ 2026-09-08 owner：「相關下拉選單…防呆機制」。
    `accessible_case_codes` 給了就只算**那些案**上的承辦 ——
    業務同仁的下拉此前列出全公司每一位承辦（含他一個案都碰不到的人），
    選了就是空表，而畫面上看不出是範圍造成的。
    `None` ＝不限縮（管理員／全公司視角）。
    """
    all_codes = ("ARRAY(SELECT case_code FROM contract_projects WHERE case_code IS NOT NULL"
                 " UNION SELECT case_code FROM pm_cases WHERE case_code IS NOT NULL)")
    params: dict[str, Any] = {}
    if accessible_case_codes is None:
        codes_expr = all_codes
    else:
        codes_expr = "CAST(:codes AS text[])"
        params["codes"] = list(accessible_case_codes) or ["__none__"]
    rows = (await db.execute(text(f"""
        SELECT user_id, name, count(DISTINCT case_code) AS n
          FROM ({_ASSIGNMENTS_BY_CASE.replace(':cs', codes_expr)}) t
         GROUP BY 1, 2
         ORDER BY 3 DESC, 2
    """), params)).all()
    return [{"user_id": r.user_id, "name": r.name, "case_count": int(r.n or 0)} for r in rows]


async def filter_case_codes_by_staff(
    db: AsyncSession, case_codes: Iterable[str], staff_user_id: Optional[int]
) -> Optional[set[str]]:
    """回「這些案號裡屬於該承辦的那些」；`staff_user_id` 為 None 時回 None（不限縮）。"""
    if staff_user_id is None:
        return None
    mine = await case_codes_of_user(db, staff_user_id)
    return {c for c in case_codes if c and c in mine}
