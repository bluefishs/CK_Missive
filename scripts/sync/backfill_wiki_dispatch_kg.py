#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案 X Phase 2: Wiki dispatch frontmatter 補 kg_entity_id

Phase 1（dispatch_kg_ingest.py）已將 127 dispatch ingest 進 canonical_entities。
本腳本：對每個 wiki/entities/*_派工單號*.md：
1. 讀 frontmatter title（即 dispatch_no）
2. 查 KG canonical_entities WHERE entity_type='dispatch' AND canonical_name=title
3. 若 kg_entity_id 已存在 → skip（idempotent）
4. 否則 frontmatter 加 kg_entity_id

用法：
    python scripts/sync/backfill_wiki_dispatch_kg.py            # dry-run
    python scripts/sync/backfill_wiki_dispatch_kg.py --apply    # 實際改 wiki

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


async def load_kg_dispatch_map(conn) -> dict[str, int]:
    """canonical_name → id"""
    rows = await conn.fetch(
        "SELECT id, canonical_name FROM canonical_entities WHERE entity_type='dispatch'"
    )
    return {r["canonical_name"]: r["id"] for r in rows}


def parse_wiki(path: Path) -> dict | None:
    """讀 wiki frontmatter，回傳 {title, entity_type, kg_entity_id, raw}"""
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
    title_m = re.search(r"^title:\s*(.+)$", fm, re.M)
    et_m = re.search(r"^entity_type:\s*(\S+)", fm, re.M)
    kg_m = re.search(r"^kg_entity_id:\s*(\S+)", fm, re.M)

    return {
        "title": title_m.group(1).strip() if title_m else None,
        "entity_type": et_m.group(1).strip() if et_m else None,
        "kg_entity_id": kg_m.group(1).strip() if kg_m else None,
        "fm_end": end,
        "fm_text": fm,
        "raw": raw,
    }


def add_kg_id_to_frontmatter(raw: str, fm_text: str, fm_end: int, kg_id: int) -> str:
    """在 frontmatter 適當位置插入 kg_entity_id"""
    # 若已有 kg_entity_id 行（NULL/None），替換
    if re.search(r"^kg_entity_id:", fm_text, re.M):
        new_fm = re.sub(
            r"^kg_entity_id:.*$",
            f"kg_entity_id: {kg_id}",
            fm_text,
            count=1,
            flags=re.M,
        )
        return raw[:3] + new_fm + raw[3 + len(fm_text):]
    # 否則於 title 行後插入
    new_fm = re.sub(
        r"^(title:.*)$",
        rf"\1\nkg_entity_id: {kg_id}",
        fm_text,
        count=1,
        flags=re.M,
    )
    return raw[:3] + new_fm + raw[3 + len(fm_text):]


async def main(apply: bool) -> int:
    if not WIKI_ENTITIES.is_dir():
        print(f"ERROR: {WIKI_ENTITIES} 不存在", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(DSN)
    try:
        kg_map = await load_kg_dispatch_map(conn)
    finally:
        await conn.close()

    print(f"=== Wiki dispatch frontmatter backfill（{'APPLY' if apply else 'DRY-RUN'}）===")
    print(f"KG dispatch entities: {len(kg_map)}")

    stats = {"matched": 0, "no_match": 0, "already_linked": 0, "non_dispatch": 0, "error": 0}
    actions = []

    for f in sorted(WIKI_ENTITIES.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        info = parse_wiki(f)
        if not info or info.get("entity_type") != "dispatch":
            stats["non_dispatch"] += 1
            continue
        if info.get("kg_entity_id") and info["kg_entity_id"] not in ("None", "null", "~", ""):
            stats["already_linked"] += 1
            continue
        title = info.get("title")
        if not title:
            stats["error"] += 1
            continue
        kg_id = kg_map.get(title)
        if kg_id is None:
            stats["no_match"] += 1
            actions.append(("NO MATCH", f.name, title))
            continue
        stats["matched"] += 1
        actions.append(("WILL LINK", f.name, f"kg_id={kg_id}"))

        if apply:
            new_raw = add_kg_id_to_frontmatter(
                info["raw"], info["fm_text"], info["fm_end"], kg_id
            )
            f.write_text(new_raw, encoding="utf-8")

    print(f"\nResults:")
    for k, v in stats.items():
        print(f"  {k:18} {v}")

    print(f"\nSample (前 5 actions):")
    for action, name, info in actions[:5]:
        print(f"  [{action}] {name:35} {info}")

    if not apply:
        print("\n（dry-run，未改 wiki；加 --apply 執行）")
    else:
        # 避免 Windows cp950 對 Unicode 符號失敗
        msg = f"\n[OK] Backfilled {stats['matched']} wiki dispatch with kg_entity_id"
        try:
            print(msg)
        except UnicodeEncodeError:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="實際改 wiki frontmatter")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.apply)))
