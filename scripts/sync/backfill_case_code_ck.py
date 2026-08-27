#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 legacy 案號轉為正式建案案號 `CK{年}_PM_{類別}_{流水}`。

## 為什麼需要這支

owner 2026-08-27~28 釐清後確立的編號職責：

    建案案號 case_code    CK{年}_PM_{類別}_{流水}   案子的身分，跨三張表的橋樑
    成案編號 project_code CK{年}_{類別}_{流水}      ＝建案案號去掉 `_PM_`
    報價單編號            B115-C020-0 / quotation_no  一張報價單（含版次）

而**匯入路徑跳過了建案編號程序**：報價單彙整匯入時把「報價單編號」直接寫進
`case_code`，於是 249 個 pm_cases 的 case_code 裝的是報價單編號。

後果：`promote_to_project()` 的新規則是「去掉 `_PM_`」，legacy 案號去不了 ⇒
**175 個已承攬的案子無法成案**（而它們的畫面看起來流程已經走完）。

## 這支做什麼

對每一筆 legacy `case_code`，產生一個新的 `CK{年}_PM_{類別}_{流水}`，
並在**三張表**同步替換（case_code 是橋樑，只改一張會把鏈路打斷）：

    pm_cases.case_code
    erp_quotations.case_code
    contract_projects.case_code
    project_user_assignments.case_code

舊值保存在 `erp_quotations.legacy_quotation_no`（該欄位本來就是為此存在），
所以**轉換後仍可用舊編號回溯**，回簽 PDF 掛回也不受影響。

## 刻意不做的事

* **不合併版次**。`B114-A016-2` 與 `-3` 是同一個案子的兩版，現在是兩筆
  pm_cases，轉換後會得到兩個不同的建案案號。合併是**語意變更**（兩筆併一筆），
  風險與這支的機械式替換不同級，應該分開決定。本支只做 1:1 轉換。
* **不動已成案的**（預設）。它們的 `project_code` 已依舊規則配發，
  改 case_code 不會讓它們變好，只會擴大影響面。用 `--scope all` 可涵蓋。

## 用法

    python scripts/sync/backfill_case_code_ck.py                  # dry-run（預設）
    python scripts/sync/backfill_case_code_ck.py --scope all      # dry-run，含已成案
    python scripts/sync/backfill_case_code_ck.py --apply          # 真的寫入

退出碼：0 正常／2 探測失敗或有阻斷性問題（不下結論）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONTAINER = "ck_missive_postgres"
DB_USER = "ck_user"
DB_NAME = "ck_documents"

#: 待轉換的 pm_cases。`--scope pending` 只取「已承攬但還沒成案」的，
#: 那是本次真正的阻塞點；`--scope all` 取全部 legacy。
_SQL_TARGETS = """
SELECT json_agg(row_to_json(t)) FROM (
  SELECT p.id, p.case_code, p.case_name, p.year, p.category,
         COALESCE(p.contract_amount, 0) AS amount,
         EXISTS (SELECT 1 FROM contract_projects c WHERE c.case_code = p.case_code) AS promoted,
         EXISTS (SELECT 1 FROM contract_projects c2
                  WHERE btrim(c2.project_name) = btrim(p.case_name)
                    AND c2.year = p.year) AS name_dup
    FROM pm_cases p
   WHERE p.case_code !~ '^CK'
     {extra}
   ORDER BY p.year, p.case_code
) t
"""

#: 既有 CK 案號的最大流水號（同一 prefix）。產號要接在它後面。
_SQL_MAXSERIAL = """
SELECT json_agg(row_to_json(t)) FROM (
  SELECT prefix, MAX(serial) AS max_serial FROM (
    SELECT substring(case_code from '^(CK[0-9]{4}_PM_[0-9]{2}_)') AS prefix,
           NULLIF(regexp_replace(case_code, '^CK[0-9]{4}_PM_[0-9]{2}_', ''), '')::int AS serial
      FROM pm_cases WHERE case_code ~ '^CK[0-9]{4}_PM_[0-9]{2}_[0-9]+$'
    UNION ALL
    SELECT substring(case_code from '^(CK[0-9]{4}_PM_[0-9]{2}_)'),
           NULLIF(regexp_replace(case_code, '^CK[0-9]{4}_PM_[0-9]{2}_', ''), '')::int
      FROM erp_quotations WHERE case_code ~ '^CK[0-9]{4}_PM_[0-9]{2}_[0-9]+$'
    UNION ALL
    SELECT substring(case_code from '^(CK[0-9]{4}_PM_[0-9]{2}_)'),
           NULLIF(regexp_replace(case_code, '^CK[0-9]{4}_PM_[0-9]{2}_', ''), '')::int
      FROM contract_projects WHERE case_code ~ '^CK[0-9]{4}_PM_[0-9]{2}_[0-9]+$'
  ) s WHERE prefix IS NOT NULL GROUP BY prefix
) t
"""

#: 每個 legacy case_code 在各表的引用筆數 —— 用來確認替換不會漏掉哪一張表。
_SQL_REFS = """
SELECT json_agg(row_to_json(t)) FROM (
  SELECT case_code, SUM(pm) pm, SUM(q) q, SUM(cp) cp, SUM(ua) ua FROM (
    SELECT case_code, 1 pm, 0 q, 0 cp, 0 ua FROM pm_cases              WHERE case_code !~ '^CK'
    UNION ALL SELECT case_code, 0, 1, 0, 0 FROM erp_quotations         WHERE case_code !~ '^CK'
    UNION ALL SELECT case_code, 0, 0, 1, 0 FROM contract_projects      WHERE case_code !~ '^CK'
    UNION ALL SELECT case_code, 0, 0, 0, 1 FROM project_user_assignments
              WHERE case_code IS NOT NULL AND case_code !~ '^CK'
  ) u GROUP BY case_code
) t
"""


def q(sql: str):
    """跑一段回傳單一 json 的 SQL。探測不到就 None —— 不下結論。"""
    try:
        r = subprocess.run(
            ["docker", "exec", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-tA", "-c", sql],
            capture_output=True, timeout=180,
        )
    except FileNotFoundError:
        print("[RED] 找不到 docker CLI —— 無法取得資料", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[RED] 查詢逾時", file=sys.stderr)
        return None
    if r.returncode != 0:
        print(f"[RED] 查詢失敗：{(r.stderr or b'').decode('utf-8', 'replace')[:300]}", file=sys.stderr)
        return None
    out = (r.stdout or b"").decode("utf-8", "replace").strip()
    if not out or out == "":
        return []
    try:
        return json.loads(out) or []
    except json.JSONDecodeError as e:
        print(f"[RED] 回傳不是 JSON：{e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("pending", "all"), default="pending",
                    help="pending=只轉「已承攬但未成案」（預設）；all=全部 legacy")
    ap.add_argument("--apply", action="store_true", help="真的寫入（預設只列印）")
    args = ap.parse_args()

    extra = ("" if args.scope == "all" else
             "AND p.status = 'contracted' AND NOT EXISTS "
             "(SELECT 1 FROM contract_projects c WHERE c.case_code = p.case_code)")

    targets = q(_SQL_TARGETS.format(extra=extra))
    maxser = q(_SQL_MAXSERIAL)
    refs = q(_SQL_REFS)
    if targets is None or maxser is None or refs is None:
        return 2
    if not targets:
        print("沒有需要轉換的 legacy 案號。")
        return 0

    #: 既有的所有 case_code —— 用來**實查**新號碼會不會撞，
    #: 而不是只靠「從最大流水號接續」這個推論。
    #: 推論在「既有號碼有缺號」時仍成立，但在「別的表有而 maxserial 沒掃到」
    #: 時會失效 —— 那正是 2026-07-31 承攬案件那次撞號的成因。
    existing = q("""
    SELECT json_agg(c) FROM (
      SELECT case_code c FROM pm_cases
      UNION SELECT case_code FROM erp_quotations
      UNION SELECT case_code FROM contract_projects
    ) t WHERE c IS NOT NULL
    """)
    if existing is None:
        return 2
    existing = set(existing)

    ref_map = {r["case_code"]: r for r in refs}
    serial = {r["prefix"]: int(r["max_serial"] or 0) for r in maxser}

    plan, seen_new = [], set()
    for t in targets:
        year = int(t["year"] or 0)
        if year and year < 1911:
            year += 1911
        cat = (t["category"] or "01")[:2].zfill(2)
        prefix = f"CK{year}_PM_{cat}_"
        serial[prefix] = serial.get(prefix, 0) + 1
        new_code = f"{prefix}{serial[prefix]:03d}"
        # 產出的號碼互不重複 —— 08-20 那次就是這裡出的事
        assert new_code not in seen_new, f"產生了重複的案號：{new_code}"
        assert new_code not in existing, (
            f"新案號 {new_code} 與資料庫既有的撞號 —— "
            "產號起點算錯了，不要繼續。")
        seen_new.add(new_code)
        r = ref_map.get(t["case_code"], {})
        plan.append({**t, "new_code": new_code,
                     "refs": {k: int(r.get(k) or 0) for k in ("pm", "q", "cp", "ua")}})

    print("=" * 78)
    print(f"legacy 案號 -> 建案案號  |  scope={args.scope}  "
          f"|  {'**寫入模式**' if args.apply else 'dry-run（不寫入）'}")
    print("=" * 78)
    print(f"  待轉換             : {len(plan)}")
    print(f"  產生的新案號互異   : {len(seen_new)}  -> "
          f"{'OK' if len(seen_new) == len(plan) else '**有重複**'}")
    print(f"  與既有案號零相撞   : 已逐筆實查 {len(existing)} 個既有案號  -> OK")
    blocked_amt = [p for p in plan if not p["promoted"] and float(p["amount"]) <= 0]
    blocked_dup = [p for p in plan if not p["promoted"] and p["name_dup"]]
    print(f"  轉換後可直接成案   : "
          f"{len([p for p in plan if not p['promoted'] and float(p['amount']) > 0 and not p['name_dup']])}")
    print(f"  轉換後仍被防重擋   : {len(blocked_dup)}   （同名同年度，多半是已建過只是沒接上）")
    print(f"  轉換後仍缺合約金額 : {len(blocked_amt)}")

    tot = defaultdict(int)
    for p in plan:
        for k, v in p["refs"].items():
            tot[k] += v
    print(f"\n  要一併替換的引用   : pm_cases {tot['pm']}／報價單 {tot['q']}／"
          f"承攬案件 {tot['cp']}／承辦同仁 {tot['ua']}")

    print("\n  前 12 筆對照：")
    for p in plan[:12]:
        flag = ""
        if p["name_dup"]:
            flag = "  [同名，成案會被擋]"
        elif float(p["amount"]) <= 0:
            flag = "  [缺金額，成案會被擋]"
        print(f"    {p['case_code']:<18} -> {p['new_code']:<18} "
              f"{str(p['case_name'])[:22]}{flag}")
    if len(plan) > 12:
        print(f"    …… 其餘 {len(plan) - 12} 筆")

    if not args.apply:
        print("\n  這是 dry-run，**沒有寫入任何東西**。")
        print("  確認無誤後加 --apply 執行；執行前請先備份（scripts/backup/）。")
        return 0

    print("\n  [寫入模式] 尚未實作 —— 需 owner 明確確認上表後再開放。", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
