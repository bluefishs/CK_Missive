#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dispatch KG entities pgvector embedding backfill（試點 — 127 筆）

⚠️ 異質同工登記 H2（docs/architecture/HETEROGENEOUS_WORK_REGISTRY.md）
   本腳本為【host 緊急/手動工具】，直呼 httpx → ollama /api/embed（見下方 OLLAMA_URL），
   **繞過** EmbeddingManager/ai_connector（SSOT）→ 冷啟動暖機/模型/重試邏輯不共用、可能漂移。
   正常補 embedding 的 SSOT 路徑＝容器內 cross_domain_contribution_service.backfill_embeddings
   或每日 04:30 cron `kg_embedding_backfill`。本腳本僅供 host 端存量止血。

延續方案 X Phase 1+2，補完 embedding 維度（768D nomic-embed-text）。

設計：
- 對 entity_type='dispatch' 且 embedding IS NULL 跑 ollama nomic-embed-text
- 文本 = canonical_name + " " + description
- 直呼 httpx /api/embed（**非** ai_connector；見上方 H2 警告）(zero cost, local Ollama)
- 批次更新（每 10 筆 commit 一次以利中斷恢復）

用法：
    python scripts/sync/backfill_dispatch_embeddings.py            # dry-run
    python scripts/sync/backfill_dispatch_embeddings.py --apply    # 實際 UPDATE

Version: 1.0.0 (2026-04-25)
範圍：本腳本僅試點 dispatch 127 筆；全 KG 21K 需另設計 nightly batch
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


async def generate_embedding(client: httpx.AsyncClient, text: str) -> Optional[list]:
    """Call Ollama /api/embed for nomic-embed-text 768D"""
    try:
        resp = await client.post(
            OLLAMA_URL,
            json={"model": EMBED_MODEL, "input": text},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        # Ollama 回 {"embeddings": [[...768 floats...]]}
        embs = data.get("embeddings") or []
        if embs and isinstance(embs[0], list):
            return embs[0]
        return None
    except Exception as e:
        print(f"  embedding error: {e}", file=sys.stderr)
        return None


async def main(apply: bool, limit: int) -> int:
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            """
            SELECT id, canonical_name, description
            FROM canonical_entities
            WHERE entity_type='dispatch' AND embedding IS NULL
            ORDER BY id
            LIMIT $1
            """,
            limit,
        )
        total = len(rows)
        print(f"=== Dispatch embedding backfill ({'APPLY' if apply else 'DRY-RUN'}) ===")
        print(f"Pending dispatch entities: {total}")
        if total == 0:
            print("✓ 全部已有 embedding")
            return 0

        if not apply:
            print("樣本：")
            for r in rows[:3]:
                text = f"{r['canonical_name']} {r['description'] or ''}".strip()
                print(f"  id={r['id']} text={text[:60]}")
            print("\n（dry-run；加 --apply 執行）")
            return 0

        # 實際生成 + UPDATE
        print(f"Calling Ollama {EMBED_MODEL} for {total} entities...")
        t0 = time.time()
        success = 0
        failed = 0
        async with httpx.AsyncClient() as client:
            for i, r in enumerate(rows, 1):
                text = f"{r['canonical_name']} {r['description'] or ''}".strip()
                emb = await generate_embedding(client, text)
                if emb is None:
                    failed += 1
                    print(f"  [{i}/{total}] FAILED id={r['id']}")
                    continue
                # UPDATE 用 vector literal '[a,b,c,...]'
                vec_literal = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
                await conn.execute(
                    "UPDATE canonical_entities SET embedding=$1::vector, updated_at=NOW() WHERE id=$2",
                    vec_literal, r["id"],
                )
                success += 1
                if i % 20 == 0:
                    elapsed = time.time() - t0
                    rate = i / max(elapsed, 0.01)
                    eta = (total - i) / max(rate, 0.01)
                    print(f"  [{i}/{total}] elapsed={elapsed:.0f}s rate={rate:.1f}/s eta={eta:.0f}s")

        elapsed = time.time() - t0
        print(f"\n✓ Backfilled: {success}/{total}, failed: {failed}, time: {elapsed:.0f}s")

        # 驗證
        cnt = await conn.fetchval(
            "SELECT COUNT(*) FROM canonical_entities WHERE entity_type='dispatch' AND embedding IS NOT NULL"
        )
        print(f"Final dispatch with embedding: {cnt}/127")

        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.apply, args.limit)))
