#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""案件狀態一致性：PM 案「已承攬」⇔ 承攬案存在 ⇔ 三表 project_code 對齊（weekly 105）。

2026-09-04 金流複查抓到的形狀：匯入服務對總表「已成立」的列寫 `status=contracted`
**但不建承攬案** ⇒ 16 筆 PM 案標已承攬、承攬案列表看不到、報價單沒有 `project_code`、
損益摘要把它們當未成案、掛在上面的請款在成案口徑裡消失 —— 而每一張表單獨看都「正常」。
另 12 筆 GN 承攬案（2020–2024 舊案）`project_code` 空，報價單跟著空。

## 判準

RED（狀態互相矛盾，不可能同時為真）：
  ① PM `status=contracted` 但沒有同 case_code 的承攬案（基線內的只 YELLOW）
  ② 承攬案存在，但 PM／報價單的 `project_code` 空或與承攬案不同
  ③ 承攬案自己的 `project_code` 空（GN 制＝case_code，PM 制＝去 `_PM_`）
  ④ 承攬案 `已結案` 而 PM 不是 `closed`（sync_from_contract 白名單漏了狀態的同型）
YELLOW：
  ⑤ ① 裡登記在基線的（同名承攬案已存在＝疑似重複建案、或 owner 裁示沿用他案），要人判
  ⑥ 未成案報價單卻掛著請款（總表說有請款＝其實已承攬；與 ① 常是同一批）
連不到 DB → YELLOW（未驗）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402

try:  # Windows 主控台預設 cp950，⇔／🔴 會直接炸掉（hooks-guide 的編碼要求同族）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 已知、待 owner 判的（09-04）：同名承攬案已在別的案號下（疑似同一件工作建兩次）；243 是 owner 裁示沿用 190。
# ⚠️ 登記不是把它變綠：這些 PM 案仍標已承攬而沒有承攬案，只是「有人知道」。判完就從這裡拿掉。
BASELINE = {
    "CK2026_PM_01_006": "owner 09-02 裁示：與 190 同一案、沿用 190 的承攬案",
    "CK2024_PM_02_002": "同名承攬案 CK2024_PM_02_001／CK2025_PM_02_005 已存在（苗栗通霄 1355，四筆兩案？）",
    "CK2025_PM_02_006": "同上，與 CK2024_PM_02_002 也同名",
    "CK2025_PM_02_058": "同名承攬案 CK2025_PM_02_057 已存在",
    "CK2025_PM_02_074": "同名承攬案 CK2025_PM_02_188 已存在",
    "CK2025_PM_02_077": "同名承攬案 CK2025_PM_02_076 已存在",
    "CK2026_PM_02_028": "同名「建物第一次測量」承攬案 3 件已存在（名稱太泛，可能不是同案）",
    "CK2026_PM_02_030": "同名承攬案 CK2026_PM_02_029 已存在",
    "CK2026_PM_02_004": "同名承攬案 CK2026_PM_02_003 已存在",
    "CK2026_PM_02_064": "同名「建物第一次測量」承攬案 3 件已存在（名稱太泛）",
}

SQL = """
SELECT json_build_object(
  'r1', (SELECT json_agg(json_build_array(pm.id, pm.case_code, left(pm.case_name,30), pm.contract_amount::bigint)) FROM pm_cases pm
          WHERE pm.status='contracted' AND NOT EXISTS (SELECT 1 FROM contract_projects cp WHERE cp.case_code=pm.case_code)),
  'r2', (SELECT json_agg(json_build_array(x.kind, x.id, x.case_code, x.pc, cp.project_code)) FROM (
            SELECT 'pm' AS kind, id, case_code, COALESCE(project_code,'') AS pc FROM pm_cases
            UNION ALL
            SELECT 'quotation', id, case_code, COALESCE(project_code,'') FROM erp_quotations WHERE deleted_at IS NULL) x
          JOIN contract_projects cp ON cp.case_code=x.case_code WHERE cp.project_code<>'' AND x.pc<>cp.project_code),
  'r3', (SELECT json_agg(json_build_array(id, case_code, left(project_name,30))) FROM contract_projects WHERE project_code IS NULL OR project_code=''),
  'r4', (SELECT json_agg(json_build_array(pm.id, pm.case_code, pm.status, cp.status)) FROM pm_cases pm JOIN contract_projects cp ON cp.case_code=pm.case_code
          WHERE cp.status='已結案' AND pm.status<>'closed'),
  'y6', (SELECT json_agg(json_build_array(q.id, q.case_code, b.billing_amount::bigint)) FROM erp_billings b JOIN erp_quotations q ON q.id=b.erp_quotation_id
          WHERE q.deleted_at IS NULL AND NOT EXISTS (SELECT 1 FROM contract_projects cp WHERE cp.case_code=q.case_code)),
  'n_pm', (SELECT count(*) FROM pm_cases WHERE status='contracted'),
  'n_cp', (SELECT count(*) FROM contract_projects)
)::text
"""


def _fetch():
    code = ("import asyncio\nfrom sqlalchemy import text\nfrom app.db.database import AsyncSessionLocal\n"
            f"SQL = {SQL!r}\nasync def m():\n    async with AsyncSessionLocal() as db:\n        print('JSON:' + (await db.execute(text(SQL))).scalar())\nasyncio.run(m())\n")
    out = python_in(code, timeout=120)
    if not out:
        return None
    line = [ln for ln in out.splitlines() if ln.startswith("JSON:")]
    return json.loads(line[-1][5:]) if line else None


def main() -> int:
    print("=== 案件狀態一致性：已承攬 ⇔ 承攬案 ⇔ project_code（weekly 105）===")
    d = _fetch()
    if d is None:
        print("  [YELLOW] 連不到容器／資料庫 —— **未驗**")
        return 1
    print(f"  PM 已承攬 {d['n_pm']}｜承攬案 {d['n_cp']}")
    reds, yels = [], []
    r1 = d.get("r1") or []
    r1_new = [r for r in r1 if r[1] not in BASELINE]
    r1_known = [r for r in r1 if r[1] in BASELINE]
    if r1_new:
        print(f"\n  🔴 ① PM 已承攬但沒有承攬案（不在基線）：{len(r1_new)}")
        for r in r1_new[:8]:
            print(f"     #{r[0]:<4} {r[1]:<22} {r[2]}  {r[3] or 0:,}")
        reds.append(("① 已承攬無承攬案", len(r1_new)))
    if r1_known:
        yels.append(("⑤ 已承攬無承攬案（基線內待判）", len(r1_known)))
    stale = [c for c in BASELINE if c not in {r[1] for r in r1}]
    if stale:
        yels.append((f"基線已過期（已處理，請移除）{stale}", len(stale)))
    for key, label in [("r2", "② PM／報價單 project_code 與承攬案不一致"), ("r3", "③ 承攬案 project_code 空"), ("r4", "④ 承攬案已結案而 PM 未 closed")]:
        rows = d.get(key) or []
        if rows:
            print(f"\n  🔴 {label}：{len(rows)}")
            for r in rows[:6]:
                print(f"     {r}")
            reds.append((label, len(rows)))
    y6 = d.get("y6") or []
    if y6:
        yels.append(("⑥ 未成案報價單掛著請款", len(y6)))
        print(f"\n  ⚠ ⑥ 未成案報價單掛著請款：{len(y6)}（總表說有請款 ⇒ 其實已承攬；多半與 ① 同批）")
        for r in y6[:6]:
            print(f"     {r}")
    print()
    if reds:
        print(f"Status: [RED] {'、'.join(f'{l} {n}' for l, n in reds)}")
        return 2
    if yels:
        print(f"Status: [YELLOW] {'、'.join(f'{l} {n}' for l, n in yels)}")
        return 1
    print("Status: [GREEN] 已承攬 ⇔ 承攬案 ⇔ project_code 三方一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
