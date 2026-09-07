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


async def case_codes_of_user(db: AsyncSession, user_id: int) -> set[str]:
    """某個人被指派到的所有 case_code（兩條綁法都算）。

    給「只看我的」這種**使用者自己選的**篩選用。
    ⚠️ 這不是 RLS —— 可見範圍由伺服器依身分決定（見 `_quotation_scope`），
    本函式只回答「這個人的案有哪些」，呼叫端要自己決定拿它做什麼。
    """
    rows = (await db.execute(text("""
        SELECT DISTINCT pa.case_code
          FROM project_user_assignments pa
         WHERE pa.user_id = :uid AND pa.case_code IS NOT NULL
           AND COALESCE(pa.status, 'active') <> 'inactive'
        UNION
        SELECT DISTINCT cp.case_code
          FROM project_user_assignments pa2
          JOIN contract_projects cp ON cp.id = pa2.project_id
         WHERE pa2.user_id = :uid AND cp.case_code IS NOT NULL
           AND COALESCE(pa2.status, 'active') <> 'inactive'
    """), {"uid": int(user_id)})).all()
    return {r[0] for r in rows if r[0]}


async def assignable_staff(db: AsyncSession) -> list[dict[str, Any]]:
    """承辦同仁下拉的選項＝**實際有被指派過的人**，不是全體使用者。

    為什麼不列全體：下拉列出沒有任何案的人，選了就是一片空白，
    使用者會以為是系統壞了。選項只給選了有東西的。
    """
    rows = (await db.execute(text(f"""
        SELECT user_id, name, count(DISTINCT case_code) AS n
          FROM ({_ASSIGNMENTS_BY_CASE.replace(':cs', 'ARRAY(SELECT case_code FROM contract_projects WHERE case_code IS NOT NULL UNION SELECT case_code FROM pm_cases WHERE case_code IS NOT NULL)')}) t
         GROUP BY 1, 2
         ORDER BY 3 DESC, 2
    """))).all()
    return [{"user_id": r.user_id, "name": r.name, "case_count": int(r.n or 0)} for r in rows]


async def filter_case_codes_by_staff(
    db: AsyncSession, case_codes: Iterable[str], staff_user_id: Optional[int]
) -> Optional[set[str]]:
    """回「這些案號裡屬於該承辦的那些」；`staff_user_id` 為 None 時回 None（不限縮）。"""
    if staff_user_id is None:
        return None
    mine = await case_codes_of_user(db, staff_user_id)
    return {c for c in case_codes if c and c in mine}
