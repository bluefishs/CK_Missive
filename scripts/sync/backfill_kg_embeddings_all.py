#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全 KG canonical_entities pgvector embedding backfill

延續 backfill_dispatch_embeddings.py 試點（127 筆 4 秒成功）：
- Ollama nomic-embed-text 768D, 30/s rate, zero cost
- 全 KG 21,575 entities 估算 ~12 min

策略：
- 按 entity_type 分組跑（可中斷重啟）
- 預設只跑業務 critical types（dispatch / project / org）— 約 ~2,700 筆 < 2 min
- --all 跑全部 21K（含 tender_record/py_*/ts_*）— ~12 min

用法：
    python scripts/sync/backfill_kg_embeddings_all.py                    # dry-run critical
    python scripts/sync/backfill_kg_embeddings_all.py --apply            # apply critical types
    python scripts/sync/backfill_kg_embeddings_all.py --apply --all      # apply 全 21K
    python scripts/sync/backfill_kg_embeddings_all.py --apply --types tender_record,project

Version: 1.0.0 (2026-04-25)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from typing import Optional

try:
    import asyncpg
    import httpx
except ImportError as e:
    print(f"missing dep: {e}", file=sys.stderr)
    sys.exit(1)

DSN = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"
OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"

# 業務 critical types（不含程式碼結構類）
CRITICAL_TYPES = ["dispatch", "project", "org", "tender_agency", "erp_quotation", "service", "agency"]


async def generate_embedding(client: httpx.AsyncClient, text: str) -> Optional[list]:
    try:
        resp = await client.post(
            OLLAMA_URL,
            json={"model": EMBED_MODEL, "input": text},
            timeout=30.0,
        )
        resp.raise_for_status()
        embs = resp.json().get("embeddings") or []
        return embs[0] if embs else None
    except Exception as e:
        print(f"  embed error: {e}", file=sys.stderr)
        return None


async def run_for_type(conn, client, entity_type: str, apply: bool) -> tuple[int, int, float]:
    """跑單一 entity_type，回傳 (success, failed, elapsed_seconds)"""
    rows = await conn.fetch(
        """
        SELECT id, canonical_name, description
        FROM canonical_entities
        WHERE entity_type = $1 AND embedding IS NULL
        ORDER BY id
        """,
        entity_type,
    )
    if not rows:
        return 0, 0, 0.0

    print(f"\n[{entity_type}] {len(rows)} pending entities")
    if not apply:
        print(f"  dry-run: 預計 backfill {len(rows)} 筆")
        return 0, 0, 0.0

    t0 = time.time()
    success = failed = 0
    for i, r in enumerate(rows, 1):
        text = f"{r['canonical_name']} {r['description'] or ''}".strip()[:2000]  # 截斷避免超長
        emb = await generate_embedding(client, text)
        if emb is None:
            failed += 1
            continue
        vec_literal = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
        await conn.execute(
            "UPDATE canonical_entities SET embedding=$1::vector, updated_at=NOW() WHERE id=$2",
            vec_literal, r["id"],
        )
        success += 1
        if i % 100 == 0:
            elapsed = time.time() - t0
            rate = i / max(elapsed, 0.01)
            eta = (len(rows) - i) / max(rate, 0.01)
            print(f"  [{i}/{len(rows)}] rate={rate:.1f}/s eta={eta:.0f}s")
    elapsed = time.time() - t0
    print(f"  ✓ {entity_type}: success={success} failed={failed} in {elapsed:.0f}s")
    return success, failed, elapsed


async def main(apply: bool, all_types: bool, types_filter: Optional[str]) -> int:
    conn = await asyncpg.connect(DSN)
    try:
        # 決定要跑哪些 types
        if types_filter:
            target_types = [t.strip() for t in types_filter.split(",")]
        elif all_types:
            rows = await conn.fetch(
                "SELECT entity_type, COUNT(*) FILTER (WHERE embedding IS NULL) AS pending "
                "FROM canonical_entities GROUP BY entity_type "
                "HAVING COUNT(*) FILTER (WHERE embedding IS NULL) > 0 "
                "ORDER BY pending DESC"
            )
            target_types = [r["entity_type"] for r in rows]
        else:
            target_types = CRITICAL_TYPES

        # 統計總量
        total_pending = await conn.fetchval(
            "SELECT COUNT(*) FROM canonical_entities WHERE embedding IS NULL AND entity_type = ANY($1::text[])",
            target_types,
        )
        print(f"=== KG embedding backfill ({'APPLY' if apply else 'DRY-RUN'}) ===")
        print(f"Target types: {target_types}")
        print(f"Total pending: {total_pending}")
        if not apply:
            print(f"預計時間 (~30/s): {total_pending // 30}s = {total_pending // 1800} min\n（dry-run；加 --apply 執行）")
            return 0

        async with httpx.AsyncClient() as client:
            grand_success = grand_failed = 0
            grand_t0 = time.time()
            for et in target_types:
                s, f, _ = await run_for_type(conn, client, et, apply=True)
                grand_success += s
                grand_failed += f
            grand_elapsed = time.time() - grand_t0

        print(f"\n=== Total ===")
        print(f"  success: {grand_success}")
        print(f"  failed:  {grand_failed}")
        print(f"  time:    {grand_elapsed:.0f}s ({grand_elapsed/60:.1f} min)")

        # 驗證最終覆蓋率
        coverage = await conn.fetch(
            "SELECT entity_type, COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS w, COUNT(*) AS t "
            "FROM canonical_entities WHERE entity_type = ANY($1::text[]) "
            "GROUP BY entity_type ORDER BY t DESC",
            target_types,
        )
        print(f"\nFinal coverage:")
        for r in coverage:
            pct = r["w"] * 100 // max(r["t"], 1)
            print(f"  {r['entity_type']:20} {r['w']:>6}/{r['t']:<6} ({pct}%)")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--all", action="store_true", help="跑全部 21K（含 py_*/ts_*）")
    parser.add_argument("--types", type=str, default=None, help="指定 types（逗號分隔）")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.apply, args.all, args.types)))
