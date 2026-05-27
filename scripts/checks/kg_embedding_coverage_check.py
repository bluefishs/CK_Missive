#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: KG pgvector embedding 覆蓋率審計

2026-04-25 方案 X 執行時意外發現的更大隱性缺口：
- canonical_entities 表 21K+ 筆，但 embedding column 全 NULL
- pgvector 768D 形同空架構
- 影響：RAG 語意搜尋失效，無法做 vector similarity 查詢
- ADR-0022 Memory Wiki 自我進化的核心能力（embedding-based recall）受限

本 detector 統計 by entity_type 的 embedding 覆蓋率，找出最大缺口；
Backfill 需另寫腳本（涉及 LLM 呼叫成本評估，可能跑數小時）。

用法：
    python scripts/checks/kg_embedding_coverage_check.py
    python scripts/checks/kg_embedding_coverage_check.py --threshold 50
    python scripts/checks/kg_embedding_coverage_check.py --ci

Version: 1.0.0 (2026-04-25)
關聯:
- ADR-0022 Memory Wiki Self-Evolving Assistant
- docs/architecture/CONSCIOUSNESS_INTEGRATION_ANALYSIS.md（待加 §10 此發現）
- backend/app/services/ai/graph/embedding_backfill_service.py (若存在)
"""
from __future__ import annotations

import argparse
import asyncio
import sys

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import asyncpg
except ImportError:
    print("需要 asyncpg", file=sys.stderr)
    sys.exit(1)


DSN = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"


async def main(threshold: int, ci: bool) -> int:
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            """
            SELECT
                entity_type,
                COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_emb,
                COUNT(*) AS total
            FROM canonical_entities
            GROUP BY entity_type
            ORDER BY total DESC
            """
        )

        grand_total = sum(r["total"] for r in rows)
        grand_with = sum(r["with_emb"] for r in rows)
        grand_rate = grand_with * 100 // max(grand_total, 1)

        print("=== KG pgvector embedding coverage ===\n")
        status = "✓" if grand_rate >= threshold else "✗"
        print(f"{status} 整體覆蓋率: {grand_with:,}/{grand_total:,} ({grand_rate}%)")
        print(f"   閾值: {threshold}%（pgvector 768D RAG 需求）\n")

        print(f"{'entity_type':28} {'with_emb':>10} {'total':>10} {'rate':>8}")
        print("-" * 65)
        for r in rows:
            rate = r["with_emb"] * 100 // max(r["total"], 1)
            flag = ""
            if r["total"] >= 100 and rate < 20:
                flag = " 🔴 RAG-blind"
            elif r["total"] >= 50 and rate < 50:
                flag = " 🟡 partial"
            print(f"{r['entity_type']:28} {r['with_emb']:>10,} {r['total']:>10,} {rate:>7}%{flag}")

        if grand_rate < threshold:
            print(f"\n⚠️  整體覆蓋率 {grand_rate}% < {threshold}%（系統性缺口）")
            print("\n影響：")
            print("  - RAG 向量搜尋無法返回相關 entity（vector similarity 0）")
            print("  - cross-domain link 失去語意基礎")
            print("  - Memory Wiki 自我進化受限（無 embedding-based recall）")
            print("\n建議路徑：")
            print("  1. 確認 backend/app/services/ai/graph/ 是否有 embedding pipeline")
            print("  2. 排程 nightly job 跑 backfill（控制 LLM 呼叫節奏）")
            print("  3. 優先補 critical types：dispatch / project / org（業務核心）")
            print("  4. 考慮 batch via Ollama nomic-embed-text（zero cost）")

            if ci:
                return 1

        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--threshold", type=int, default=50, help="覆蓋率閾值（預設 50%%）")
    parser.add_argument("--ci", action="store_true", help="低於閾值 exit 1")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.threshold, args.ci)))
