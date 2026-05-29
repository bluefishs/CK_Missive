"""ADR-0046 task E：MEDIUM review queue 健康度 audit (L51, 2026-05-29)

監控 1,469 筆 MEDIUM 候選的 admin review 進度，防 backlog 永遠 pending
（dead queue 反模式，L29 family 教訓）。

Thresholds:
- RED: pending > 5000 (queue 滿載，admin 沒消化)
- YELLOW: pending > 2000 或 oldest pending > 30d (慢但仍動)
- GREEN: 其他

Usage:
  python scripts/checks/tender_review_queue_audit.py
  python scripts/checks/tender_review_queue_audit.py --strict  # exit 1 on RED
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta

# 允許從 backend/ 跑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


async def main(strict: bool = False) -> int:
    from app.db.database import async_session_maker
    from sqlalchemy import text

    async with async_session_maker() as db:
        # 1. 統計各 status
        r = await db.execute(text("""
            SELECT status, COUNT(*) AS cnt, MIN(created_at) AS oldest, MAX(created_at) AS newest
            FROM tender_match_review GROUP BY status
        """))
        rows = r.mappings().all()
        stats = {row["status"]: row for row in rows}

        pending = stats.get("pending", {})
        approved = stats.get("approved", {})
        rejected = stats.get("rejected", {})

        pending_cnt = int(pending.get("cnt", 0))
        approved_cnt = int(approved.get("cnt", 0))
        rejected_cnt = int(rejected.get("cnt", 0))
        total = pending_cnt + approved_cnt + rejected_cnt

        # 最舊 pending（review 怠工指標）
        oldest_pending = pending.get("oldest")
        oldest_pending_age_days = 0
        if oldest_pending:
            oldest_pending_age_days = (datetime.now() - oldest_pending).days

        # admin review 進度比例
        reviewed_cnt = approved_cnt + rejected_cnt
        review_progress_pct = (reviewed_cnt * 100.0 / total) if total > 0 else 0.0

        # 判定 level
        if pending_cnt > 5000:
            level = "RED"
            reason = f"queue overflow pending={pending_cnt} > 5000"
        elif pending_cnt > 2000 or oldest_pending_age_days > 30:
            level = "YELLOW"
            reason = (
                f"backlog warning: pending={pending_cnt}, "
                f"oldest_age={oldest_pending_age_days}d"
            )
        else:
            level = "GREEN"
            reason = (
                f"healthy: pending={pending_cnt}, "
                f"review_progress={review_progress_pct:.1f}%"
            )

        # Output
        print(f"=== Tender Enrichment Review Queue Audit (ADR-0046 task E) ===")
        print(f"Status: [{level}] {reason}")
        print(f"")
        print(f"Stats:")
        print(f"  pending:  {pending_cnt:>6d}")
        print(f"  approved: {approved_cnt:>6d}")
        print(f"  rejected: {rejected_cnt:>6d}")
        print(f"  total:    {total:>6d}")
        print(f"")
        print(f"Review progress: {review_progress_pct:.1f}% "
              f"({reviewed_cnt} of {total} reviewed)")
        if oldest_pending:
            print(f"Oldest pending: {oldest_pending} (age {oldest_pending_age_days} days)")

        if strict and level == "RED":
            return 1
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on RED (for fitness gate)")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(strict=args.strict)))
