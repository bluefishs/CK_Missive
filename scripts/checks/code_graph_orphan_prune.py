#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程式圖譜 orphan 安全 prune（保守子集：真刪除 = symbol 全專案都不存在）

★ 授權執行（2026-07-17，owner 選 A）：承 code_graph_orphan_audit（step 68）揭發
  2032 orphan（主因 Wave 1-8 搬檔）。本腳本只處理**最保守子集**＝orphan 且該
  symbol 在**專案任何 .py 都不存在**（＝真刪除，非搬移）。搬移型（symbol 在別處）
  一律排除——那需「重指路徑」而非刪除。

安全設計（[[feedback_rigor_no_self_inflicted_instability]]）：
  1. 保守子集：symbol nowhere in backend/*.py（排除搬移，只剪真刪）
  2. --apply 前**完整備份**被刪的 canonical_entities 列 + 5 張 cascade 表關聯列到
     backups/ 的 SQL（可 restore）。cascade：entity_aliases/document_entity_mentions/
     entity_relationships(src+tgt)/taoyuan_dispatch_entity_link 皆 ON DELETE CASCADE。
  3. 硬刪（因 valid_to 未被任何查詢消費，soft-delete 無效）；備份使可回溯。
  4. 只刪 graph_domain='code'（不碰業務 KG）。

用法：
    python scripts/checks/code_graph_orphan_prune.py             # DRY-RUN（預設，只報）
    python scripts/checks/code_graph_orphan_prune.py --apply     # 備份後刪除
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import asyncpg
except ImportError:
    print("需要 asyncpg", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
DSN = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"
PY_TYPES = ("py_function", "py_class", "api_endpoint", "service", "repository", "schema")
BACKEND = ROOT / "backend"


def normalize_path(fpath: str) -> Path | None:
    if not fpath:
        return None
    fpath = fpath.replace("\\", "/")
    if "CK_Missive/" in fpath:
        rel = fpath.split("CK_Missive/", 1)[1]
    elif fpath.startswith("/app/"):
        rel = "backend/" + fpath[len("/app/"):]
    elif fpath.startswith(("backend/", "frontend/")):
        rel = fpath
    else:
        return None
    return ROOT / rel


def build_symbol_index() -> set[str]:
    """全 backend/*.py 定義的 symbol 名集合（def/async def/class 的名稱）。"""
    idx: set[str] = set()
    pat = re.compile(r"^\s*(?:async\s+def|def|class)\s+([A-Za-z_]\w*)", re.M)
    for p in BACKEND.rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        idx.update(pat.findall(txt))
    return idx


def symbol_defined_in(text: str, symbol: str) -> bool:
    return bool(re.search(rf"^\s*(?:async\s+def|def|class)\s+{re.escape(symbol)}\b", text, re.M))


async def find_true_deletions(conn) -> list[dict]:
    rows = await conn.fetch(f"""
        SELECT id, canonical_name, description::jsonb->>'file_path' AS fpath
        FROM canonical_entities
        WHERE graph_domain='code' AND entity_type IN {PY_TYPES} AND description IS NOT NULL
    """)
    symbol_index = build_symbol_index()  # 全專案存在的 symbol 名
    file_cache: dict[Path, str | None] = {}
    true_del = []
    for r in rows:
        name = r["canonical_name"]
        if "::" not in name:
            continue
        symbol = name.split("::")[-1].split(".")[-1]
        if not symbol or symbol == "__init__":
            continue
        p = normalize_path(r["fpath"] or "")
        if p is None:
            continue
        if p not in file_cache:
            try:
                file_cache[p] = p.read_text(encoding="utf-8", errors="ignore") if p.exists() else None
            except Exception:
                file_cache[p] = None
        text = file_cache[p]
        is_orphan = text is None or not symbol_defined_in(text, symbol)
        if is_orphan and symbol not in symbol_index:
            # orphan 且 symbol 全專案都不存在 → 真刪除（保守）
            true_del.append({"id": r["id"], "name": name, "symbol": symbol})
    return true_del


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    conn = await asyncpg.connect(DSN)
    try:
        print("=" * 66)
        print("程式圖譜 orphan 安全 prune（保守子集：symbol 全專案不存在＝真刪除）")
        print("=" * 66)
        targets = await find_true_deletions(conn)
        ids = [t["id"] for t in targets]
        print(f"\n真刪除 orphan（保守子集）：{len(targets)}")
        # 依模組聚合
        from collections import Counter
        mods = Counter(t["name"].split("::")[0] for t in targets)
        print("\n分布 top 15：")
        for mod, n in mods.most_common(15):
            print(f"  {n:4d}  {mod}")
        print("\n樣本 10：")
        for t in targets[:10]:
            print(f"  {t['name']}")

        if not args.apply:
            print("\n" + "=" * 66)
            print(f"DRY-RUN：{len(targets)} 筆真刪除候選。--apply 才會備份+刪除。")
            return 0

        if not ids:
            print("\n無可刪除，結束。")
            return 0

        # 完整備份（CSV，可 restore；另有今晨全庫 backup 作雙保險）
        bdir = ROOT / "backups" / "code_graph_prune"
        bdir.mkdir(parents=True, exist_ok=True)
        id_list = ",".join(str(i) for i in ids)
        print(f"\n備份 {len(ids)} 筆 entity + cascade 關聯列 → {bdir} ...")
        backup_specs = [
            ("canonical_entities", f"SELECT * FROM canonical_entities WHERE id IN ({id_list})"),
            ("entity_aliases", f"SELECT * FROM entity_aliases WHERE canonical_entity_id IN ({id_list})"),
            ("document_entity_mentions", f"SELECT * FROM document_entity_mentions WHERE canonical_entity_id IN ({id_list})"),
            ("taoyuan_dispatch_entity_link", f"SELECT * FROM taoyuan_dispatch_entity_link WHERE canonical_entity_id IN ({id_list})"),
            ("entity_relationships", f"SELECT * FROM entity_relationships WHERE source_entity_id IN ({id_list}) OR target_entity_id IN ({id_list})"),
        ]
        for tbl, q in backup_specs:
            fp = bdir / f"{tbl}_20260717.csv"
            with open(fp, "wb") as f:
                await conn.copy_from_query(q, output=f, format="csv", header=True)
            cnt = sum(1 for _ in open(fp, encoding="utf-8", errors="ignore")) - 1
            print(f"  備份 {tbl}: {cnt} rows → {fp.name}")
        # 記 id 清單供追溯
        (bdir / "pruned_ids_20260717.txt").write_text(
            "\n".join(f'{t["id"]}\t{t["name"]}' for t in targets), encoding="utf-8")

        # 刪除（cascade 自動處理關聯表）
        print("\n執行刪除（cascade 自動處理關聯表）...")
        deleted = await conn.execute(f"DELETE FROM canonical_entities WHERE id IN ({id_list})")
        print(f"  {deleted}")
        remain = await conn.fetchval("SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code'")
        print(f"  code entity 剩餘：{remain}（刪除前 11779）")
        print(f"\n✅ 完成。備份在 {bdir}（可 restore）；今晨全庫 backup 作雙保險。")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
