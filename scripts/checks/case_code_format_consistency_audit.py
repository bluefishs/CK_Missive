#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""案號新制統一與填報編碼同步（weekly 102）。

owner 2026-09-02 晚：「統一新制避免混淆，對應填報編碼同步檢核」。

## 三種格式並存的來歷

| 來源 | project_code | case_code |
|---|---|---|
| PM 建案 → 成案（`promote_to_project`） | 建案案號去 `_PM_`：`CK2026_01_008` | `CK2026_PM_01_008` |
| 手動建承攬案（`contract/core.py`，09-02 晚改） | ＝case_code：`CK2026_GN_01_003` | `CK2026_GN_01_003` |
| **舊制**（09-02 之前手動建）| `CK2025_01_01_003`（含作業性質碼） | GN 或空 |

「01」在舊制是類別、在新制是模組 —— 同一個位置兩種意思，這就是混淆的來源。
存量舊制不動（首跑量到 **78** 筆，不是文件裡估的 23；documents／taoyuan 引用著），**新建一律新制**。

## 判準

① **新建承攬案（本檢核上線 2026-09-03 之後 created）不得是舊制格式** —— RED。
   舊制的形狀：`CK\d{4}_\d{2}_\d{2}_\d{3}`（第二段是兩位數字＝類別碼）。
② **成案編碼可回溯建案案號**：project_code 必須 = case_code 或 = case_code 去 `_PM_`
   （新建者）；對不上代表有人手打了一個號 —— RED。
③ **報價單的 project_code 必須等於其 case_code 對應承攬案的 project_code** —— 對不上 RED
   （填報時抄錯號，金流會掛到錯的案子）。
④ **新建報價單 quote_kind 不得為 NULL** —— 三條建立路徑都該帶值，NULL 代表有第四條路。
⑤ `legacy_quotation_no` 重複 —— RED（有唯一索引，這條只是雙保險；索引被拿掉時還能叫）。

連不到 DB → YELLOW（未驗），不回 GREEN。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402

CUTOFF = "2026-09-03"

SQL = f"""
SELECT json_build_object(
  'legacy_new', (SELECT json_agg(json_build_array(id, project_code, case_code)) FROM contract_projects
                  WHERE created_at >= '{CUTOFF}' AND project_code ~ '^CK\\d{{4}}_\\d{{2}}_\\d{{2}}_\\d{{3}}$'),
  'untraceable', (SELECT json_agg(json_build_array(id, project_code, case_code)) FROM contract_projects
                  WHERE created_at >= '{CUTOFF}' AND case_code IS NOT NULL
                    AND project_code <> case_code AND project_code <> replace(case_code, '_PM_', '_')),
  'quote_pc_mismatch', (SELECT json_agg(json_build_array(q.id, q.project_code, c.project_code)) FROM erp_quotations q
                  JOIN contract_projects c ON c.case_code=q.case_code
                  WHERE q.deleted_at IS NULL AND q.project_code IS NOT NULL AND q.project_code <> c.project_code),
  'kind_null_new', (SELECT count(*) FROM erp_quotations WHERE deleted_at IS NULL AND created_at >= '{CUTOFF}' AND quote_kind IS NULL),
  'legacy_dup', (SELECT json_agg(json_build_array(legacy_quotation_no, n)) FROM (SELECT legacy_quotation_no, count(*) n FROM erp_quotations WHERE deleted_at IS NULL AND legacy_quotation_no IS NOT NULL GROUP BY 1 HAVING count(*)>1) d),
  'legacy_total', (SELECT count(*) FROM contract_projects WHERE project_code ~ '^CK\\d{{4}}_\\d{{2}}_\\d{{2}}_\\d{{3}}$'),
  'total', (SELECT count(*) FROM contract_projects)
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
    print("=== 案號新制統一與填報編碼同步（weekly 102）===")
    d = _fetch()
    if d is None:
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**")
        return 1
    print(f"  承攬案 {d['total']}｜舊制格式存量 {d['legacy_total']}（{CUTOFF} 之前建的，不判）")
    reds = []
    for key, label in [("legacy_new", "① 新建承攬案仍是舊制格式"), ("untraceable", "② 成案編碼對不回建案案號"),
                       ("quote_pc_mismatch", "③ 報價單 project_code ≠ 承攬案 project_code"), ("legacy_dup", "⑤ legacy_quotation_no 重複")]:
        rows = d.get(key) or []
        if rows:
            print(f"\n  🔴 {label}：{len(rows)} 件")
            for r in rows[:8]:
                print(f"     {r}")
            reds.append((label, len(rows)))
    if d.get("kind_null_new"):
        print(f"\n  🔴 ④ 新建報價單 quote_kind 為 NULL：{d['kind_null_new']} 件（有第四條建立路徑沒帶值）")
        reds.append(("④ quote_kind NULL", d["kind_null_new"]))
    print()
    if reds:
        print(f"Status: [RED] {'、'.join(f'{l} {n}' for l, n in reds)}")
        return 2
    print("Status: [GREEN] 新建案號全為新制、成案編碼可回溯、報價單編碼與承攬案一致、quote_kind 齊、legacy 無重複")
    return 0


if __name__ == "__main__":
    sys.exit(main())
