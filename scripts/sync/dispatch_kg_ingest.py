#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案 X Phase 1: Dispatch → KG canonical_entities ingest

CONSCIOUSNESS_INTEGRATION_ANALYSIS.md §4.2 + WIKI_KG_BACKFILL_STRATEGY.md 方案 X

從 PG taoyuan_dispatch_orders（127 筆）建立 KG canonical_entities entries：
- entity_type = 'dispatch'（新值，varchar 無需 migration）
- canonical_name = dispatch_no（如 "112年_派工單號001"）
- linked_project_id = contract_project_id（用既有欄位連父 project）
- external_id = "dispatch:{id}"
- source_project = "ck-missive"
- description = project_name（業務上下文）
- embedding = NULL（pgvector backfill 排程另跑）

用法：
    python scripts/sync/dispatch_kg_ingest.py            # dry-run
    python scripts/sync/dispatch_kg_ingest.py --apply    # 實際 INSERT

idempotent：以 external_id 為 unique key，重跑不重複 INSERT。

Version: 1.0.0 (2026-04-25)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Optional

try:
    import asyncpg
except ImportError:
    print("需要 asyncpg: pip install asyncpg", file=sys.stderr)
    sys.exit(1)


DSN = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"


async def list_dispatches(conn) -> list:
    return await conn.fetch(
        """
        SELECT id, dispatch_no, contract_project_id, project_name, work_type
        FROM taoyuan_dispatch_orders
        ORDER BY id
        """
    )


async def find_existing(conn, external_ids: list) -> set:
    if not external_ids:
        return set()
    rows = await conn.fetch(
        """
        SELECT external_id FROM canonical_entities
        WHERE entity_type = 'dispatch' AND external_id = ANY($1::text[])
        """,
        external_ids,
    )
    return {r["external_id"] for r in rows}


async def insert_dispatch(conn, dispatch: dict) -> int:
    """INSERT 一筆 dispatch entity，回傳新 id

    注意：linked_project_id 不填（FK→taoyuan_projects，但 dispatch 的
    contract_project_id 指向 contract_projects，schema 不對齊）。
    contract_project_id 寫入 description 內供未來查詢；正式 cross-domain edge
    建議走 entity_relations 表。
    """
    contract_pid = dispatch.get("contract_project_id")
    desc_parts = [dispatch.get("project_name") or ""]
    if contract_pid:
        desc_parts.append(f"[contract_project_id={contract_pid}]")
    return await conn.fetchval(
        """
        INSERT INTO canonical_entities (
            canonical_name,
            entity_type,
            description,
            alias_count,
            mention_count,
            first_seen_at,
            last_seen_at,
            created_at,
            updated_at,
            source_project,
            external_id
        ) VALUES (
            $1, 'dispatch', $2, 0, 0,
            NOW(), NOW(), NOW(), NOW(),
            'ck-missive', $3
        )
        RETURNING id
        """,
        dispatch["dispatch_no"],
        " ".join(desc_parts).strip(),
        f'dispatch:{dispatch["id"]}',
    )


async def main(apply: bool) -> int:
    conn = await asyncpg.connect(DSN)
    try:
        dispatches = await list_dispatches(conn)
        print(f"=== Dispatch → KG ingest（{'APPLY' if apply else 'DRY-RUN'}）===")
        print(f"PG dispatches: {len(dispatches)}")

        external_ids = [f'dispatch:{d["id"]}' for d in dispatches]
        existing = await find_existing(conn, external_ids)
        print(f"Existing in KG: {len(existing)}")

        to_insert = [d for d in dispatches if f'dispatch:{d["id"]}' not in existing]
        print(f"New to insert:  {len(to_insert)}")
        print()

        # 樣本
        if to_insert:
            print("Sample (前 3 筆預計 INSERT):")
            for d in to_insert[:3]:
                print(
                    f"  canonical_name={d['dispatch_no']:25} "
                    f"linked_project_id={d['contract_project_id']} "
                    f"description={(d.get('project_name') or '')[:40]}"
                )
            print()

        if not apply:
            print("（dry-run，未實際 INSERT；加 --apply 執行）")
            return 0

        # 實際 INSERT
        if not to_insert:
            print("✓ 全部已存在，無需 INSERT")
            return 0

        inserted = 0
        async with conn.transaction():
            for d in to_insert:
                new_id = await insert_dispatch(conn, dict(d))
                inserted += 1
        print(f"✓ Inserted {inserted} dispatch entities to KG canonical_entities")

        # 驗證
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM canonical_entities WHERE entity_type='dispatch'"
        )
        print(f"Final KG dispatch entities: {total}")
        return 0

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="實際 INSERT（dry-run 預設）")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.apply)))
