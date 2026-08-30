#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性：為既有 kb_chunks 補上 file_hash（不重新向量化）。

## 為什麼需要它

2026-08-30 為 `kb_chunks` 加了 `file_hash`（增量同步的比對鍵），
既有 2,343 段全部是 NULL。而增量邏輯把 NULL 視為「需重建」
⇒ **第一次同步等於全重建**，實測從 host 跑 >10 分鐘還沒完。

那 2,343 段的向量本來就是從同一批 docs 嵌出來的。只要內容沒變，
補上 hash 就好，**沒有理由重嵌一次**。

## ⚠️ 但不能無條件蓋章

chunks 是過去某個時點嵌的，docs 之後可能改過。
若把**現在**的 hash 蓋到**舊內容**產生的 chunks 上，
就等於把「已經過期」標記成「最新」——**把漂移藏起來**，
而這正是增量機制要防的東西。

⇒ 判準是**逐段比對內容**：用現在的檔案重新分段，與 DB 裡該 file_path
的 chunks（依 chunk_index 排序）逐段比對。
  · 完全一致 → 蓋 hash（它確實是最新的）
  · 不一致   → **維持 NULL**，讓下次增量同步重建它
  · 來源檔已不存在 → 不處理（增量同步會清掉）

用法：
    python scripts/sync/backfill_kb_chunk_file_hash.py            # dry-run
    python scripts/sync/backfill_kb_chunk_file_hash.py --apply    # 實際寫入
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://ck_user:ck_password_2024@127.0.0.1:5434/ck_documents",
)


async def main(apply: bool) -> int:
    from sqlalchemy import text

    from app.core.paths import DOCS_DIR
    from app.db.database import async_session_maker
    from app.services.ai.misc.kb_embedding import _split_markdown_sections

    stamped = drifted = missing = 0
    drift_examples: list[str] = []

    async with async_session_maker() as db:
        rows = (await db.execute(
            text("SELECT DISTINCT file_path FROM kb_chunks WHERE file_hash IS NULL")
        )).all()
        paths = [r[0] for r in rows]
        print(f"待處理 file_path：{len(paths)} 個")

        for rel in paths:
            src = DOCS_DIR / rel
            if not src.is_file():
                missing += 1
                continue
            try:
                content = src.read_text(encoding="utf-8")
            except Exception:
                missing += 1
                continue

            sections = _split_markdown_sections(content)
            db_chunks = (await db.execute(
                text("SELECT content FROM kb_chunks WHERE file_path = :p "
                     "ORDER BY chunk_index"),
                {"p": rel},
            )).all()

            same = (
                len(sections) == len(db_chunks)
                and all(s["content"] == c[0] for s, c in zip(sections, db_chunks))
            )
            if not same:
                drifted += 1
                if len(drift_examples) < 5:
                    drift_examples.append(
                        f"{rel}（現在 {len(sections)} 段 / DB {len(db_chunks)} 段）"
                    )
                continue

            if apply:
                md5 = hashlib.md5(content.encode("utf-8")).hexdigest()
                await db.execute(
                    text("UPDATE kb_chunks SET file_hash = :h WHERE file_path = :p"),
                    {"h": md5, "p": rel},
                )
            stamped += 1

        if apply:
            await db.commit()

    print()
    print(f"  內容一致、{'已蓋' if apply else '可蓋'} hash：{stamped}")
    print(f"  內容已變、維持 NULL（下次同步重建）：{drifted}")
    print(f"  來源檔不存在（同步時會清掉）：{missing}")
    if drift_examples:
        print("\n  已變動的例子：")
        for e in drift_examples:
            print(f"    · {e}")
    if not apply:
        print("\n（dry-run，未寫入；加 --apply 執行）")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="實際寫入 file_hash")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.apply)))
