#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把「沒有上游建案的 `_PM_` 格式案號」改為誠實的 GN 案號。

## 為什麼需要這支（H1，2026-08-29 專案管理域複查）

15 筆 contract_projects 的 case_code 長得像 PM 建案案號（`CK{年}_PM_…`），
但 pm_cases 裡**沒有**對應的列 —— 12 筆是歷史存量（已結案、無成案編號）、
3 筆是 2026-08-18 前直接建立承攬案件時誤用 PM 產號器產生的
（`contract/core.py` 當日已改用 GN，並註明「既有存量改名屬 owner 決定」；
owner 2026-08-29 於 /loop 裁示「轉換格式…逐一辦理」）。

危害：假 PM 案號佔用 PM 產號空間、`cross_module_lookup` PM 側永遠 None、
畫面上點不進建案（竹崎 `CK2026_PM_01_009` 即實例）。

## 做法

GN 序號接在既有 `CK{年}_GN_{類別}_` 最大值之後；與全庫三表案號逐筆實查
零相撞後，在**單一交易**內同步替換八張帶 case_code 的表：
contract_projects / erp_quotations / assets / expense_invoices /
finance_ledgers / pm_case_attachments / project_user_assignments /
tender_bookmarks。交易內斷言：八表舊碼歸零、承攬案件新碼筆數相符、
報價單橋接數不變。

刻意不動的：22 筆 `case_code = project_code` 自我回填（成案編號格式，
不冒充 PM，橋樑在承攬側自洽）；不補造 pm_cases（歷史的正確狀態是
「沒有」，不是「補一個」）。

## 用法

    python scripts/sync/rename_orphan_pm_case_codes.py            # dry-run
    python scripts/sync/rename_orphan_pm_case_codes.py --apply    # 寫入

退出碼：0 正常／2 探測失敗或阻斷性問題。
"""
from __future__ import annotations

import argparse
import collections
import re
import subprocess
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONTAINER = "ck_missive_postgres"
DB = ["docker", "exec", CONTAINER, "psql", "-U", "ck_user", "-d", "ck_documents"]

TABLES = [
    "contract_projects", "erp_quotations", "assets", "expense_invoices",
    "finance_ledgers", "pm_case_attachments", "project_user_assignments",
    "tender_bookmarks",
]


def q(sql: str):
    r = subprocess.run(DB + ["-tA", "-F", "|", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    if r.returncode != 0:
        print(f"[RED] 查詢失敗：{r.stderr[:300]}", file=sys.stderr)
        return None
    return [line.split("|") for line in r.stdout.splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的寫入（預設只列印）")
    args = ap.parse_args()

    rows = q(r"""SELECT c.id, c.case_code FROM contract_projects c
        WHERE c.case_code LIKE 'CK%\_PM\_%'
          AND NOT EXISTS (SELECT 1 FROM pm_cases p WHERE p.case_code = c.case_code)
        ORDER BY c.case_code""")
    gn = q(r"SELECT case_code FROM contract_projects WHERE case_code LIKE 'CK%\_GN\_%'")
    codes = q("""SELECT case_code FROM pm_cases WHERE case_code IS NOT NULL
        UNION SELECT case_code FROM erp_quotations WHERE case_code IS NOT NULL
        UNION SELECT case_code FROM contract_projects WHERE case_code IS NOT NULL""")
    if rows is None or gn is None or codes is None:
        return 2
    if not rows:
        print("沒有需要改名的 _PM_ 孤兒案號。")
        return 0

    all_codes = {r[0] for r in codes}
    serial: collections.Counter = collections.Counter()
    for (code,) in gn:
        m = re.match(r"CK(\d{4})_GN_(\d{2})_(\d+)", code)
        if m:
            key = (m.group(1), m.group(2))
            serial[key] = max(serial[key], int(m.group(3)))

    mapping: list[tuple[str, str]] = []
    for _id, old in rows:
        m = re.match(r"CK(\d{4})_PM_(\d{2})_\d+", old)
        if not m:
            print(f"[RED] 非預期格式：{old}", file=sys.stderr)
            return 2
        yr, cat = m.group(1), m.group(2)
        serial[(yr, cat)] += 1
        new = f"CK{yr}_GN_{cat}_{serial[(yr, cat)]:03d}"
        if new in all_codes:
            print(f"[RED] 新號 {new} 與既有撞號 —— 不要繼續", file=sys.stderr)
            return 2
        all_codes.add(new)
        mapping.append((old, new))

    print("=" * 70)
    print(f"_PM_ 孤兒案號 -> GN  |  {'**寫入模式**' if args.apply else 'dry-run（不寫入）'}")
    print("=" * 70)
    for o, n in mapping:
        print(f"  {o}  ->  {n}")
    print(f"\n  共 {len(mapping)} 筆；與全庫 {len(codes)} 個既有案號逐筆實查零相撞。")

    if not args.apply:
        print("\n  這是 dry-run，沒有寫入任何東西。確認後加 --apply。")
        return 0

    values = ",\n".join(f"('{o}','{n}')" for o, n in mapping)
    updates = "\n".join(
        f"UPDATE {t} x SET case_code = m.new_code FROM _h1_map m WHERE x.case_code = m.old_code;"
        for t in TABLES)
    checks = " + ".join(
        f"(SELECT count(*) FROM {t} x JOIN _h1_map m ON x.case_code = m.old_code)"
        for t in TABLES)
    sql = f"""\\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _h1_map (old_code text PRIMARY KEY, new_code text UNIQUE) ON COMMIT DROP;
INSERT INTO _h1_map VALUES
{values};
{updates}
DO $$
DECLARE leftover int; cp int; qj int;
BEGIN
  SELECT {checks} INTO leftover;
  IF leftover > 0 THEN RAISE EXCEPTION '仍有 % 處舊碼 — 回滾', leftover; END IF;
  SELECT count(*) INTO cp FROM contract_projects c JOIN _h1_map m ON c.case_code = m.new_code;
  -- ⚠️ RAISE 的格式佔位是單一 `%`；寫成 `%%`（字面百分號）卻帶參數，
  -- PL/pgSQL 在 DO **編譯期**就報 too many parameters ⇒ 斷言永遠到不了、
  -- 交易每次整體回滾 —— 而外層只看得到「沒有 COMMIT」。第一版就是這樣
  -- 連續三次「看起來執行了、實際零寫入」。
  IF cp <> {len(mapping)} THEN RAISE EXCEPTION '承攬案件新碼 % 不符 — 回滾', cp; END IF;
  SELECT count(*) INTO qj FROM erp_quotations qt
    JOIN contract_projects c ON c.case_code = qt.case_code
    JOIN _h1_map m ON c.case_code = m.new_code;
  IF qj <> 4 THEN RAISE EXCEPTION '報價橋接 % 不符 — 回滾', qj; END IF;
END $$;
SELECT '改名完成', count(*) FROM _h1_map;
COMMIT;
"""
    # ⚠️ `docker exec` 必須帶 `-i` 才會把 stdin 傳進去 —— 第一版漏了它，
    # psql 讀到空輸入、退出碼 0、什麼都沒做，而本腳本印了 ✅。
    # 「指令成功、退出碼 0，可能是什麼都沒發生」—— 這次是自己示範。
    r = subprocess.run(["docker", "exec", "-i", CONTAINER,
                        "psql", "-U", "ck_user", "-d", "ck_documents"],
                       input=sql, capture_output=True, text=True,
                       encoding="utf-8", timeout=300)
    tags = [ln for ln in (r.stdout or "").splitlines()
            if ln.startswith(("UPDATE", "INSERT", "COMMIT"))]
    print("\n  [寫入結果] " + ("；".join(tags) if tags else "（無任何指令回報）"))
    if r.returncode != 0 or "ERROR" in (r.stderr or ""):
        print(f"  [RED] 寫入失敗，交易已回滾：\n{(r.stderr or '')[:600]}", file=sys.stderr)
        return 2

    # 寫入後**用新查詢自我複驗**，不信任上面的輸出（同型教訓的第二道保險）
    left = q(r"""SELECT count(*) FROM contract_projects c
        WHERE c.case_code LIKE 'CK%\_PM\_%'
          AND NOT EXISTS (SELECT 1 FROM pm_cases p WHERE p.case_code = c.case_code)""")
    renamed = q(r"SELECT count(*) FROM contract_projects WHERE case_code LIKE 'CK%\_GN\_%'")
    if left is None or renamed is None:
        return 2
    if int(left[0][0]) != 0:
        print(f"  [RED] 複驗失敗：仍有 {left[0][0]} 筆 _PM_ 孤兒 —— 寫入沒有生效",
              file=sys.stderr)
        return 2
    print(f"  ✅ 複驗通過：_PM_ 孤兒歸零、GN 案號現有 {renamed[0][0]} 筆。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
