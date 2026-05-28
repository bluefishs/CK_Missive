#!/usr/bin/env python3
"""
Tender ezbid ↔ PCC Match Audit (ADR-0046 Phase 2 ROI 試算)

對 DB 內所有 ezbid records 嘗試 fuzzy match PCC records，
印出預估 ROI 數據供 Phase 3-5 全套落地決策。

Match algorithm:
  Confidence = 0.5 × title_similarity (pg_trgm)
             + 0.3 × agency_match (unit_name exact)
             + 0.2 × date_proximity (announce_date ±3d)

Threshold:
  - confidence ≥ 0.85 → HIGH (auto-link)
  - confidence ≥ 0.70 → MEDIUM (manual review)
  - confidence < 0.70 → reject

Dry-run only — 不寫 DB，僅印出統計。

Version: 1.0.0
Created: 2026-05-28 (ADR-0046 Phase 2)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Container internal Python — uses app.db
sys.path.insert(0, "/app")


async def run_audit(sample_limit: Optional[int] = None, batch_size: int = 500) -> Dict[str, Any]:
    """跑全 ezbid × PCC fuzzy match，回傳統計 dict。

    Args:
        sample_limit: None = 跑全量 27k ezbid，數字 = 抽樣 N 筆驗證
        batch_size: batch 處理大小（避免 statement_timeout）

    Returns:
        {
            "total_ezbid": int,
            "total_pcc": int,
            "high_confidence": int (≥ 0.85),
            "medium_confidence": int (0.70-0.85),
            "examples_high": [...],
            "examples_medium": [...],
        }
    """
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text as sa_text

    async with AsyncSessionLocal() as db:
        # 1. 計數
        r = await db.execute(sa_text("""
            SELECT
                COUNT(*) FILTER (WHERE source = 'ezbid') AS ezbid_count,
                COUNT(*) FILTER (WHERE source = 'pcc') AS pcc_count
            FROM tender_records
        """))
        row = r.one()
        total_ezbid = row[0]
        total_pcc = row[1]

        print(f"DB 概況: ezbid={total_ezbid} / PCC={total_pcc}")
        print()

        # 2. Batched approach — 對每批 ezbid 用 LATERAL JOIN 找 best PCC match
        #    LATERAL JOIN + GIN trigram index 走 idx_tender_title_trgm
        target_ezbid = sample_limit or total_ezbid
        offset = 0
        all_matches = []
        print(f"開始 batched audit（batch={batch_size}, target={target_ezbid:,}）...")

        while offset < target_ezbid:
            batch_sql = sa_text(f"""
                WITH ezbid_batch AS (
                    SELECT id AS eid, title AS etitle, unit_name AS eunit,
                           announce_date AS edate, ezbid_id
                    FROM tender_records
                    WHERE source = 'ezbid' AND title IS NOT NULL AND title != ''
                    ORDER BY id
                    OFFSET {offset} LIMIT {batch_size}
                )
                SELECT
                    er.eid, er.etitle, er.eunit, er.edate, er.ezbid_id,
                    pcc.id AS pid, pcc.title AS ptitle, pcc.unit_name AS punit,
                    pcc.announce_date AS pdate,
                    pcc.unit_id AS pcc_unit_id, pcc.job_number AS pcc_job_number,
                    pcc.sim AS title_sim,
                    CASE WHEN er.eunit = pcc.unit_name THEN 1.0
                         WHEN similarity(COALESCE(er.eunit, ''), COALESCE(pcc.unit_name, '')) > 0.7
                              THEN similarity(er.eunit, pcc.unit_name)
                         ELSE 0.0 END AS agency_match,
                    CASE WHEN er.edate IS NOT NULL AND pcc.announce_date IS NOT NULL
                              AND ABS(er.edate - pcc.announce_date) <= 3 THEN 1.0
                         WHEN er.edate IS NOT NULL AND pcc.announce_date IS NOT NULL
                              AND ABS(er.edate - pcc.announce_date) <= 7 THEN 0.5
                         ELSE 0.0 END AS date_proximity
                FROM ezbid_batch er
                CROSS JOIN LATERAL (
                    SELECT pr.*, similarity(pr.title, er.etitle) AS sim
                    FROM tender_records pr
                    WHERE pr.source = 'pcc'
                      AND pr.title % er.etitle  -- GIN trigram index 命中
                    ORDER BY similarity(pr.title, er.etitle) DESC
                    LIMIT 1
                ) pcc
                WHERE pcc.sim > 0.5
            """)
            try:
                result = await db.execute(batch_sql)
                batch = result.fetchall()
                all_matches.extend(batch)
            except Exception as e:
                print(f"  batch offset={offset} failed: {e}")
                break
            offset += batch_size
            if offset % (batch_size * 5) == 0:
                print(f"  進度 {offset:,} / {target_ezbid:,}（matches 累計 {len(all_matches)}）")

        # 計算 confidence
        matches = []
        for m in all_matches:
            confidence = float(m.title_sim) * 0.5 + float(m.agency_match) * 0.3 + float(m.date_proximity) * 0.2
            matches.append((m, confidence))
        # filter & sort
        matches = [(m, c) for m, c in matches if c >= 0.5]
        matches.sort(key=lambda x: x[1], reverse=True)

        # 3. 分桶
        high = [(m, c) for m, c in matches if c >= 0.85]
        medium = [(m, c) for m, c in matches if 0.70 <= c < 0.85]
        low = [(m, c) for m, c in matches if c < 0.70]

        return {
            "total_ezbid": total_ezbid,
            "total_pcc": total_pcc,
            "ezbid_sample": sample_limit or total_ezbid,
            "high_confidence": len(high),
            "medium_confidence": len(medium),
            "low_confidence": len(low),
            "match_rate_high_pct": round(100 * len(high) / max(sample_limit or total_ezbid, 1), 2),
            "match_rate_medium_pct": round(100 * len(medium) / max(sample_limit or total_ezbid, 1), 2),
            "examples_high": [
                {
                    "ezbid_id": m.ezbid_id,
                    "ezbid_title": m.etitle[:60],
                    "ezbid_unit": m.eunit[:40] if m.eunit else "",
                    "pcc_unit_id": m.pcc_unit_id,
                    "pcc_job_number": m.pcc_job_number,
                    "pcc_title": m.ptitle[:60],
                    "title_sim": round(float(m.title_sim), 3),
                    "agency_match": round(float(m.agency_match), 2),
                    "date_proximity": round(float(m.date_proximity), 2),
                    "confidence": round(c, 3),
                }
                for m, c in high[:5]
            ],
            "examples_medium": [
                {
                    "ezbid_id": m.ezbid_id,
                    "ezbid_title": m.etitle[:60],
                    "pcc_title": m.ptitle[:60],
                    "title_sim": round(float(m.title_sim), 3),
                    "agency_match": round(float(m.agency_match), 2),
                    "confidence": round(c, 3),
                }
                for m, c in medium[:5]
            ],
        }


def print_report(stats: Dict[str, Any]) -> None:
    print("=" * 80)
    print(f"Tender ezbid ↔ PCC Match Audit (ADR-0046 Phase 2)")
    print("=" * 80)
    print()
    print(f"DB 概況:")
    print(f"  ezbid records: {stats['total_ezbid']:,}")
    print(f"  PCC records:   {stats['total_pcc']:,}")
    print(f"  audit sample:  {stats['ezbid_sample']:,}")
    print()
    print(f"Match 結果:")
    print(f"  HIGH (≥0.85, auto-link):    {stats['high_confidence']:>4} ({stats['match_rate_high_pct']:>5.2f}%)")
    print(f"  MEDIUM (0.70-0.85, review): {stats['medium_confidence']:>4} ({stats['match_rate_medium_pct']:>5.2f}%)")
    print(f"  LOW (<0.70, reject):        {stats['low_confidence']:>4}")
    print()

    if stats["examples_high"]:
        print("HIGH confidence 範例 (top 5):")
        for ex in stats["examples_high"]:
            print(f"  [{ex['confidence']:.3f}] ezbid({ex['ezbid_id']}) → PCC ({ex['pcc_unit_id']}/{ex['pcc_job_number']})")
            print(f"        ezbid: {ex['ezbid_title']}")
            print(f"        PCC:   {ex['pcc_title']}")
            print(f"        sim={ex['title_sim']} agency={ex['agency_match']} date={ex['date_proximity']}")
            print()

    if stats["examples_medium"]:
        print("MEDIUM confidence 範例 (top 5):")
        for ex in stats["examples_medium"]:
            print(f"  [{ex['confidence']:.3f}] ezbid({ex['ezbid_id']}): {ex['ezbid_title']}")
            print(f"                            PCC: {ex['pcc_title']}")
            print()

    # ROI 決策建議
    print("=" * 80)
    print("ROI 決策建議:")
    total_actionable = stats["high_confidence"] + stats["medium_confidence"]
    rate = stats["match_rate_high_pct"] + stats["match_rate_medium_pct"]
    if rate >= 20:
        print(f"  🟢 ROI 高（actionable {rate:.1f}% ≥ 20%）→ 推薦 Phase 3-5 全套落地")
    elif rate >= 5:
        print(f"  🟡 ROI 中（actionable {rate:.1f}% ∈ [5,20)）→ 改 v6.12 排程 / 限定 HIGH 自動 link")
    else:
        print(f"  🔴 ROI 低（actionable {rate:.1f}% < 5%）→ 建議延後 / 改 Option 3 緊急 LINE 推薦")
    print(f"  actionable matches: {total_actionable} (high+medium)")
    print("=" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(description="Tender ezbid+PCC match audit")
    parser.add_argument("--sample", type=int, default=None,
                        help="抽樣 N 筆 ezbid（None = 全量 27k）")
    parser.add_argument("--strict", action="store_true",
                        help="ROI < 5% 即 exit 1")
    args = parser.parse_args()

    stats = asyncio.run(run_audit(sample_limit=args.sample))
    print_report(stats)

    if args.strict:
        rate = stats["match_rate_high_pct"] + stats["match_rate_medium_pct"]
        if rate < 5:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
