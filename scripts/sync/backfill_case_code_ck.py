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

* **1:1 轉換，不合併尾碼相同的案號**。
  ⚠️ 我起初把 `B114-A016-2` 與 `-3` 當成「同一案的兩個版次」——**那是錯的**。
  `quotation_legacy_import._derive_case_code` 的檔頭已經記過並實測推翻：
  **子號是子案，不是版次**。實例：

      B114-B026    桃園市平鎮區平東路土地協議市價查估作業
      B114-B026-2  翠64透地雷達作業          <- 完全不同的案子

  把尾碼當版次去掉的後果實測過：**4 組被硬掛在一起、另 36 組重複建立**。
  所以 1:1 是**正確做法**，不是保守的折衷。
  （`A016-2`/`A016-3` 案名確實相同，所以實務上是混合的——而「不去尾碼」
   是安全的那一邊：掛錯的代價高於多一筆。）
  ⚠️ 回簽 PDF 掛檔那一側（`signed_quotation_import.normalize_legacy_no`）
  **刻意相反**——它忽略尾碼，因為那一側「掛不上」的代價高於「掛錯」。
  同一個欄位兩種讀法都是對的，已登記 TIER3_INTENTIONAL_DIVERGENCE_REGISTRY §10。
  **不要統一它們。**
* **不動已成案的**（預設）。它們的 `project_code` 已依舊規則配發，
  改 case_code 不會讓它們變好，只會擴大影響面。用 `--scope all` 可涵蓋。

## ⚠️ 順序相依：這支要先跑，匯入服務才能改

匯入服務（`quotation_legacy_import`）目前用 legacy 案號去比對既有 pm_cases，
而 **`pm_cases` 沒有 legacy 欄位** ⇒ 它只能拿 `case_code` 來比。

所以「讓匯入自己產建案案號」**必須等這支跑完之後**才做：
先轉換 ⇒ pm_cases 全是 CK 案號、舊編號留在 `erp_quotations.legacy_quotation_no`
⇒ 匯入改為「先用 legacy_quotation_no 找既有案子、找不到才產新號」。

反過來先改匯入，會產生「新進來的是 CK 制、既有的是 legacy 制」而兩者比對不上
⇒ **每次匯入都重複建案**。這正是 08-20 那次去尾碼造成 36 組重複的同型。

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


def _apply_plan(plan: list) -> int:
    """單一交易寫入：四張表同步替換＋交易內斷言，任何不符整體 rollback。

    2026-08-28 owner「授權執行」後補上（原本刻意只印計畫、stderr 說明未實作）。
    設計要點：
      * 對照表先進 TEMP TABLE，四張表都 JOIN 它替換 —— 不逐筆下 UPDATE，
        沒有「一筆壞掉後剩下全部陪葬」的窗口（B1 那次的教訓）。
      * `legacy_quotation_no` 為空時以舊 case_code 補上（COALESCE）——
        轉換後仍可用舊編號回溯，回簽 PDF 掛回不受影響。
      * 交易內 DO 斷言：舊碼歸零、新碼筆數＝計畫筆數，否則 RAISE ⇒ 全部回滾。
    """
    esc = lambda s: str(s).replace("'", "''")
    n = len(plan)
    values = ",\n".join(
        f"('{esc(p['case_code'])}', '{esc(p['new_code'])}')" for p in plan)
    sql = f"""
\\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _a32_map (old_code text PRIMARY KEY, new_code text UNIQUE) ON COMMIT DROP;
INSERT INTO _a32_map (old_code, new_code) VALUES
{values};

UPDATE pm_cases p SET case_code = m.new_code
  FROM _a32_map m WHERE p.case_code = m.old_code;
UPDATE erp_quotations e
   SET case_code = m.new_code,
       legacy_quotation_no = COALESCE(e.legacy_quotation_no, m.old_code)
  FROM _a32_map m WHERE e.case_code = m.old_code;
UPDATE contract_projects c SET case_code = m.new_code
  FROM _a32_map m WHERE c.case_code = m.old_code;
UPDATE project_user_assignments u SET case_code = m.new_code
  FROM _a32_map m WHERE u.case_code = m.old_code;

DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM pm_cases p JOIN _a32_map m ON p.case_code = m.old_code;
  IF bad > 0 THEN RAISE EXCEPTION 'pm_cases 還剩 % 筆舊案號未轉換 — 全部回滾', bad; END IF;
  SELECT count(*) INTO bad FROM pm_cases p JOIN _a32_map m ON p.case_code = m.new_code;
  IF bad <> {n} THEN RAISE EXCEPTION 'pm_cases 新案號 % 筆 != 計畫 {n} 筆 — 全部回滾', bad; END IF;
  SELECT count(*) INTO bad FROM erp_quotations e JOIN _a32_map m ON e.case_code = m.old_code;
  IF bad > 0 THEN RAISE EXCEPTION 'erp_quotations 還剩 % 筆舊案號 — 全部回滾', bad; END IF;
  SELECT count(*) INTO bad FROM erp_quotations e
    JOIN _a32_map m ON e.case_code = m.new_code
   WHERE e.legacy_quotation_no IS NULL;
  IF bad > 0 THEN RAISE EXCEPTION '% 筆報價單轉換後失去舊編號回溯 — 全部回滾', bad; END IF;
END $$;
COMMIT;
"""
    r = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME],
        input=sql.encode("utf-8"), capture_output=True, timeout=300,
    )
    out = (r.stdout or b"").decode("utf-8", "replace")
    err = (r.stderr or b"").decode("utf-8", "replace")
    tags = [ln for ln in out.splitlines() if ln.startswith(("UPDATE", "INSERT"))]
    print("\n  [寫入結果] " + ("；".join(tags) if tags else "（無 UPDATE 回報）"))
    if r.returncode != 0 or "ROLLBACK" in out or "ERROR" in err:
        print(f"  [RED] 寫入失敗，交易已回滾：\n{err[:800]}", file=sys.stderr)
        return 2
    print(f"  ✅ {n} 筆已轉換並通過交易內斷言（舊碼歸零／新碼 {n}／回溯欄位齊全）。")
    return 0


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

    # 2026-08-28 owner 於本表 dry-run 對照後明言「授權執行」——寫入路徑就此開放。
    return _apply_plan(plan)


if __name__ == "__main__":
    sys.exit(main())
