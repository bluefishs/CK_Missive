#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wiki project 13 個未連結 KG backfill

延續 backfill_wiki_dispatch_kg.py 模式，補 wiki entity_type=project 的 13 個未連結。

關鍵發現：wiki 的 project 對應 KG 中常為 erp_quotation type（schema 對齊）。
本腳本接受跨 entity_type 匹配（exact name match 即可）。

用法：
    python scripts/sync/backfill_wiki_project_kg.py            # dry-run
    python scripts/sync/backfill_wiki_project_kg.py --apply    # 實際改 wiki

Version: 1.0.0 (2026-04-25)
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

try:
    import asyncpg
except ImportError:
    print("需要 asyncpg", file=sys.stderr)
    sys.exit(1)


DSN = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"
WIKI_ENTITIES = Path("wiki/entities")


def parse_wiki(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    if not raw.startswith("---"):
        return None
    end = raw.find("\n---", 3)
    if end < 0:
        return None
    fm = raw[3:end]
    return {
        "title": (re.search(r"^title:\s*(.+)$", fm, re.M).group(1).strip()
                  if re.search(r"^title:\s*", fm, re.M) else None),
        "entity_type": (re.search(r"^entity_type:\s*(\S+)", fm, re.M).group(1).strip()
                        if re.search(r"^entity_type:\s*", fm, re.M) else None),
        "kg_entity_id": (re.search(r"^kg_entity_id:\s*(\S+)", fm, re.M).group(1).strip()
                         if re.search(r"^kg_entity_id:\s*", fm, re.M) else None),
        "fm_text": fm,
        "raw": raw,
    }


def add_kg_id(raw: str, fm_text: str, kg_id: int, kg_type: str | None = None) -> str:
    """加 kg_entity_id 至 frontmatter（並記錄 kg_entity_type 若不同）"""
    if re.search(r"^kg_entity_id:", fm_text, re.M):
        new_fm = re.sub(r"^kg_entity_id:.*$", f"kg_entity_id: {kg_id}", fm_text, count=1, flags=re.M)
    else:
        new_fm = re.sub(r"^(title:.*)$", rf"\1\nkg_entity_id: {kg_id}", fm_text, count=1, flags=re.M)
    return raw[:3] + new_fm + raw[3 + len(fm_text):]


async def main(apply: bool) -> int:
    conn = await asyncpg.connect(DSN)
    try:
        stats = {"matched_exact": 0, "no_match": 0, "already_linked": 0, "non_project": 0}
        actions = []

        for f in sorted(WIKI_ENTITIES.iterdir()):
            if not f.is_file() or f.suffix != ".md":
                continue
            info = parse_wiki(f)
            if not info or info.get("entity_type") != "project":
                stats["non_project"] += 1
                continue
            if info.get("kg_entity_id") and info["kg_entity_id"] not in ("None","null","~",""):
                stats["already_linked"] += 1
                continue

            title = info.get("title")
            if not title:
                continue

            # Exact match KG（不限 entity_type，接受 erp_quotation 等）
            row = await conn.fetchrow(
                "SELECT id, entity_type FROM canonical_entities WHERE canonical_name = $1 LIMIT 1",
                title,
            )
            if row:
                stats["matched_exact"] += 1
                kg_id = row["id"]
                kg_type = row["entity_type"]
                actions.append(("WILL LINK", f.name[:40], f"kg_id={kg_id} (kg_type={kg_type})"))
                if apply:
                    new_raw = add_kg_id(info["raw"], info["fm_text"], kg_id)
                    f.write_text(new_raw, encoding="utf-8")
            else:
                stats["no_match"] += 1
                actions.append(("NO MATCH", f.name[:40], title[:40]))

        print(f"=== Wiki project backfill ({'APPLY' if apply else 'DRY-RUN'}) ===\n")
        for k, v in stats.items():
            print(f"  {k:18} {v}")
        print(f"\nActions ({min(len(actions), 20)}):")
        for action, name, info in actions[:20]:
            print(f"  [{action}] {name:42} {info}")

        if not apply:
            print("\n（dry-run；加 --apply 執行）")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.apply)))
