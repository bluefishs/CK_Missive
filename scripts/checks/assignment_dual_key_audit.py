#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""承辦指派必須同時帶兩把鍵（weekly 110）——只綁一邊的指派，另一頁看不到、改不到。

owner 2026-09-05：「/erp/quotations/588 前端已修正承辦同仁為賴柏霖，系統仍顯示賴柏霖與曾廷睿，
資料庫不是對應同欄位，為何會發生？」

## 為什麼

`project_user_assignments` 有兩把鍵：`case_code`（PM 案件頁寫）與 `project_id`（承攬案人員分頁寫）。
588 的兩筆：#540 曾廷睿只綁 case_code（09-03 從 PM 頁指派）、#546 賴柏霖只綁 project_id（09-04 從承攬案頁指派）。
承攬案頁只列 project_id 那一筆，owner 在那裡「改成賴柏霖」；PM 那一筆它根本看不到，報價單的承辦欄取兩邊聯集 ⇒ 兩個名字。
08-31 把八個**讀取**點改成聯集，但**寫入**仍是各寫各的鍵——同一個人指派在兩頁各有一份事實。
09-05 回填：只綁 case_code 69 筆補 project_id、只綁 project_id 24 筆補 case_code。

## 判準

RED    指派只綁一邊而另一把鍵解得出來（case_code 對得到承攬案卻沒 project_id；或有 project_id 卻沒 case_code）
YELLOW 同案同人重複兩筆（合併後）——回填會讓它們顯形
連不到 DB → YELLOW
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402

SQL = """
SELECT json_build_object(
  'one_sided', (SELECT json_agg(json_build_array(a.id, a.user_id, a.case_code, a.project_id)) FROM project_user_assignments a
     WHERE (a.project_id IS NULL AND a.case_code IS NOT NULL AND EXISTS (SELECT 1 FROM contract_projects c WHERE c.case_code=a.case_code))
        OR (a.case_code IS NULL AND a.project_id IS NOT NULL)),
  'dup', (SELECT json_agg(json_build_array(cc, user_id, n)) FROM (
     SELECT COALESCE(a.case_code, c.case_code) cc, a.user_id, count(*) n FROM project_user_assignments a
     LEFT JOIN contract_projects c ON c.id=a.project_id GROUP BY 1,2 HAVING count(*)>1) t),
  'total', (SELECT count(*) FROM project_user_assignments)
)::text
"""


def _fetch():
    code = (
        "import asyncio\nfrom sqlalchemy import text\nfrom app.db.database import AsyncSessionLocal\n"
        f"SQL = {SQL!r}\n"
        "async def m():\n    async with AsyncSessionLocal() as db:\n        print('JSON:' + (await db.execute(text(SQL))).scalar())\n"
        "asyncio.run(m())\n"
    )
    out = python_in(code, timeout=120)
    if not out:
        return None
    line = [ln for ln in out.splitlines() if ln.startswith("JSON:")]
    return json.loads(line[-1][5:]) if line else None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=== 承辦指派雙鍵一致性（weekly 110）===")
    d = _fetch()
    if d is None:
        print("[YELLOW] 連不到 DB／容器，未驗")
        return 1
    one = d.get("one_sided") or []
    dup = d.get("dup") or []
    print(f"指派 {d.get('total')} 筆；只綁一邊 {len(one)}；同案同人重複 {len(dup)}")
    for r in one[:8]:
        print(f"  [RED] #{r[0]} user={r[1]} case_code={r[2]} project_id={r[3]}")
    for r in dup[:8]:
        print(f"  [YELLOW] {r[0]} user={r[1]} 有 {r[2]} 筆")
    if one:
        print(f"[RED] {len(one)} 筆指派只綁一邊——另一頁看不到、改不到")
        return 2
    if dup:
        print(f"[YELLOW] {len(dup)} 組同案同人重複，要人判留哪一筆")
        return 1
    print("[GREEN] 指派兩把鍵都齊")
    return 0


if __name__ == "__main__":
    sys.exit(main())
