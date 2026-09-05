#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""名稱欄與鍵欄並存的一致性（weekly 107）——「id 是鍵，名稱是快照」。

owner 2026-09-04 /loop：「由資料庫表單對應名稱標準化與語意定義釐清，避免對應錯誤或無法關聯」。

## 為什麼

同一個實體在本庫常有兩欄：一欄存名稱（`client_name`／`client_agency`／`vendor_name`）、一欄存主檔鍵
（`client_vendor_id`／`vendor_id`）。名稱是給人看的快照，鍵才是關聯用的。兩欄並存時會出三種事：
  ① 鍵是空的、而名稱其實精確對得到主檔 ——「可關聯而未關聯」，靠名稱模糊比對的頁面就時好時壞（09-04 竹崎地政、大有國際）
  ② 鍵有值、名稱與主檔不同 —— 快照漂移（張啟良建築師 vs 張啟良建築師事務所；林晉廷 vs 林宥廷測量技師事務所）
  ③ 鍵是空的、名稱對不到任何主檔 —— 主檔缺這一家（勤典工程行 ×4）
規則寫在 FIELD_SEMANTICS.md「主檔鍵與名稱快照」。

## 判準

RED   ＝ ① 可精確對上主檔卻沒填鍵（程式該自動補、沒補）。
YELLOW＝ ② 快照漂移（要人判是同一家改名、還是連錯）、③ 主檔缺（要人建）。
連不到 DB → YELLOW（未驗）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.docker_exec import python_in  # noqa: E402

# (表, 名稱欄, 鍵欄, 主檔表, 主檔名稱欄, 額外條件, 漂移判準)
# 漂移判準預設「快照 ≠ 主檔名」；公文的 sender／receiver 是文件上的原文（常帶「（協力廠商：…）」「代表」），
# 主檔名**包含在原文裡**就不算漂移，只有原文與主檔名毫無交集才是連錯——2026-09-05 owner「非常多案例皆有此問題，如何複查與排除」
# 時把 documents 納入：519 筆「≠」裡 514 筆是原文帶附註，真的可疑只有 5 筆。判準不收窄就是一支天天黃 500 筆的檢核。
_DRIFT_DEFAULT = "btrim(x.{n}) <> btrim(v.{mn})"
_DRIFT_UNRELATED = "btrim(x.{n}) <> btrim(v.{mn}) AND position(btrim(v.{mn}) IN x.{n}) = 0 AND position(btrim(x.{n}) IN v.{mn}) = 0"
PAIRS = [
    ("pm_cases", "client_name", "client_vendor_id", "partner_vendors", "vendor_name", "TRUE", _DRIFT_DEFAULT),
    ("contract_projects", "client_agency", "client_vendor_id", "partner_vendors", "vendor_name", "TRUE", _DRIFT_DEFAULT),
    ("erp_vendor_payables", "vendor_name", "vendor_id", "partner_vendors", "vendor_name", "TRUE", _DRIFT_DEFAULT),
    ("documents", "sender", "sender_agency_id", "government_agencies", "agency_name", "TRUE", _DRIFT_UNRELATED),
    ("documents", "receiver", "receiver_agency_id", "government_agencies", "agency_name", "TRUE", _DRIFT_UNRELATED),
]
# 鍵可以從來源推導卻沒填（沒有名稱欄可比對，但鍵該有）：(標籤, 計數 SQL, 說明)
DERIVED = [
    ("finance_ledgers.vendor_id ← erp_vendor_payables.vendor_id",
     "SELECT count(*) FROM finance_ledgers l JOIN erp_vendor_payables p ON p.id = l.source_id "
     "WHERE l.source_type = 'erp_vendor_payable' AND l.vendor_id IS NULL AND p.vendor_id IS NOT NULL",
     "帳本應付分錄的廠商鍵可從來源應付推導（09-05 回填 5 筆）"),
    ("contract_projects.client_agency_id（機關主檔）vs client_vendor_id（委託單位主檔）",
     "SELECT count(*) FROM contract_projects c JOIN government_agencies g ON g.id = c.client_agency_id "
     "JOIN partner_vendors v ON v.id = c.client_vendor_id WHERE btrim(g.agency_name) <> btrim(v.vendor_name)",
     "承攬案有兩把鍵指向兩個主檔（34 筆帶舊的 client_agency_id）；兩把鍵指到不同名字＝連錯"),
]


def _pair_key(t, n):
    return f"{t}.{n}"


SQL = "SELECT json_build_object(" + ",".join(
    f"""'{_pair_key(t, n)}', json_build_object(
      'linkable_unlinked', (SELECT json_agg(json_build_array(x.id, x.{n}, v.id)) FROM {t} x
          JOIN {mt} v ON btrim(v.{mn}) = btrim(x.{n})
          WHERE x.{k} IS NULL AND x.{n} IS NOT NULL AND btrim(x.{n}) <> '' AND {cond}),
      'drift', (SELECT json_agg(json_build_array(x.id, x.{n}, v.{mn})) FROM {t} x JOIN {mt} v ON v.id = x.{k}
          WHERE {drift.format(n=n, mn=mn)} AND {cond}),
      'no_master', (SELECT json_agg(json_build_array(x.id, x.{n})) FROM {t} x
          WHERE x.{k} IS NULL AND x.{n} IS NOT NULL AND btrim(x.{n}) <> ''
            AND NOT EXISTS (SELECT 1 FROM {mt} v WHERE btrim(v.{mn}) = btrim(x.{n})) AND {cond}),
      'total', (SELECT count(*) FROM {t} x WHERE {cond})
    )"""
    for (t, n, k, mt, mn, cond, drift) in PAIRS
) + "," + ",".join(f"""'derived:{label}', ({sql})""" for (label, sql, _why) in DERIVED) + ")::text"


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
    print("=== 名稱欄 vs 鍵欄一致性（weekly 107；id 是鍵、名稱是快照）===")
    d = _fetch()
    if d is None:
        print("[YELLOW] 連不到 DB／容器，未驗")
        return 1
    reds = yels = 0
    for (t, n, k, *_rest) in PAIRS:
        r = d.get(_pair_key(t, n)) or {}
        lu, dr, nm = r.get("linkable_unlinked") or [], r.get("drift") or [], r.get("no_master") or []
        print(f"\n{t}.{n} ↔ {k}（{r.get('total')} 筆）：可連未連 {len(lu)}／快照漂移 {len(dr)}／主檔缺 {len(nm)}")
        for row in lu[:5]:
            print(f"  [RED] #{row[0]} 「{row[1]}」精確對得到主檔 #{row[2]} 卻沒填鍵")
        for row in dr[:5]:
            print(f"  [YELLOW] #{row[0]} 快照「{row[1]}」≠ 主檔「{row[2]}」")
        for row in nm[:5]:
            print(f"  [YELLOW] #{row[0]} 「{row[1]}」主檔沒有這一家")
        reds += len(lu)
        yels += len(dr) + len(nm)
    print()
    for (label, _sql, why) in DERIVED:
        n_bad = int(d.get(f"derived:{label}") or 0)
        print(f"{label}：{n_bad} 筆 —— {why}")
        if n_bad:
            print(f"  [RED] {n_bad} 筆鍵可推導卻沒填／兩把鍵不一致")
        reds += n_bad
    print()
    if reds:
        print(f"[RED] {reds} 筆可關聯而未關聯——自動補鍵的路徑沒接到")
        return 2
    if yels:
        print(f"[YELLOW] 快照漂移／主檔缺 共 {yels} 筆，要人判")
        return 1
    print("[GREEN] 名稱與鍵一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
