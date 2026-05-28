#!/usr/bin/env python3
"""
Tender Enrichment Freshness Audit (fitness step 55, ADR-0046 Phase 5)

監測 ezbid → PCC enrichment 每日 03:30 cron 是否真活。

觸發：ADR-0046 Phase 5 觀測層 — 確保 enrichment scheduler 不 silent dormant
（同 L48 family）

檢查邏輯：
1. 從 DB 查最新 pcc_match_at（最近一次 enrichment apply 時間）
2. 比 NOW() - 24h
3. 若 ≥ 24h 無 enrich → RED（scheduler silent dormant 或 0 new HIGH 連續多日）

Fail mode:
- 連續 5 天 0 new HIGH 也可能是正常（PCC API 沒新公告） → MEDIUM warning
- 連續 7 天無任何 enrich activity → 強烈警訊

Version: 1.0.0
Created: 2026-05-28 (ADR-0046 Phase 5)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, "/app")


async def check_freshness() -> dict:
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text as sa_text

    async with AsyncSessionLocal() as db:
        r = await db.execute(sa_text("""
            SELECT
                COUNT(*) FILTER (WHERE pcc_match_unit_id IS NOT NULL) AS total_matched,
                COUNT(*) FILTER (
                    WHERE pcc_match_at >= NOW() - INTERVAL '24 hours'
                ) AS matched_24h,
                COUNT(*) FILTER (
                    WHERE pcc_match_at >= NOW() - INTERVAL '7 days'
                ) AS matched_7d,
                MAX(pcc_match_at) AS last_enrich_at
            FROM tender_records
            WHERE source = 'ezbid'
        """))
        row = r.one()
        last = row.last_enrich_at
        hours_since = None
        if last:
            hours_since = (datetime.utcnow() - last).total_seconds() / 3600

        return {
            "total_matched": row.total_matched,
            "matched_24h": row.matched_24h,
            "matched_7d": row.matched_7d,
            "last_enrich_at": str(last) if last else "NEVER",
            "hours_since_last": round(hours_since, 1) if hours_since is not None else None,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tender enrichment freshness")
    parser.add_argument("--strict", action="store_true",
                        help="RED 觸發 exit 1")
    args = parser.parse_args()

    print("=" * 72)
    print("[55/55] Tender Enrichment Freshness Audit (ADR-0046 Phase 5)")
    print("=" * 72)
    print()

    stats = asyncio.run(check_freshness())

    print(f"DB 狀態:")
    print(f"  total ezbid matched to PCC: {stats['total_matched']}")
    print(f"  matched in last 24h:        {stats['matched_24h']}")
    print(f"  matched in last 7d:         {stats['matched_7d']}")
    print(f"  last enrich:                {stats['last_enrich_at']}")
    if stats['hours_since_last'] is not None:
        print(f"  hours since last enrich:    {stats['hours_since_last']}")
    print()

    if stats["total_matched"] == 0:
        print("🔴 RED — never ran enrichment (pcc_match_at all NULL)")
        print("  修法指引：")
        print("  1. 確認 scheduler.py 有註冊 tender_pcc_enrichment 03:30 cron")
        print("  2. 手動觸發：docker exec ck_missive_backend python -c 'enrich_all_unmatched()'")
        return 1 if args.strict else 0

    if stats["hours_since_last"] is not None and stats["hours_since_last"] > 30:
        print(f"🔴 RED — last enrich {stats['hours_since_last']:.1f}h ago (>30h, scheduler dormant)")
        print("  與 L48 family 同型 — cron 未跑 / silent fail")
        return 1 if args.strict else 0

    if stats["matched_7d"] == 0:
        print("🟡 YELLOW — 7 day 內 0 new enrichment（可能 PCC API 無新公告）")
        return 0

    print(f"🟢 GREEN — enrichment 機制健康（24h: {stats['matched_24h']}, 7d: {stats['matched_7d']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
