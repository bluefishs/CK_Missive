"""
Tender Enrichment Service (ADR-0046 Phase 3)

ezbid → PCC fuzzy match + 高信心 auto-link 機制。

設計原則：
1. **HIGH only auto-link**（confidence ≥ 0.85 + 三重 guard）
   避免 trigram false positive（短字串/同前綴 issue）
2. MEDIUM (0.70-0.85) 不 auto，留 review queue 給人工
3. LATERAL JOIN + GIN trigram index 避免 CROSS JOIN N×M timeout
4. Batched 處理（500/batch）避免 statement_timeout

Match algorithm（同 audit script）:
  Confidence = 0.5 × title_sim (pg_trgm)
             + 0.3 × agency_match (unit_name exact / fuzzy)
             + 0.2 × date_proximity (announce_date ±3d)

HIGH guard 三重條件:
  - title_sim ≥ 0.85
  - agency exact match (unit_name 完全相同 OR similarity ≥ 0.85)
  - date diff ≤ 3 days

Version: 1.0.0
Created: 2026-05-28 (ADR-0046 Phase 3)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# 與 audit 一致的閾值
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.70

# HIGH auto-link 三重 guard
GUARD_TITLE_SIM = 0.85
GUARD_AGENCY_SIM = 0.85
GUARD_DATE_DIFF_DAYS = 3


async def find_pcc_match_for_ezbid(
    db: AsyncSession,
    ezbid_record_id: int,
) -> Optional[Dict[str, Any]]:
    """對單一 ezbid record 找最佳 PCC match。

    Returns:
        {pcc_unit_id, pcc_job_number, confidence, title_sim, agency_match, date_proximity}
        或 None（無 match 達 MEDIUM 門檻）
    """
    sql = text("""
        SELECT
            er.id AS eid,
            er.title AS etitle,
            er.unit_name AS eunit,
            er.announce_date AS edate,
            pcc.id AS pid,
            pcc.title AS ptitle,
            pcc.unit_name AS punit,
            pcc.announce_date AS pdate,
            pcc.unit_id AS pcc_unit_id,
            pcc.job_number AS pcc_job_number,
            pcc.sim AS title_sim,
            CASE WHEN er.unit_name = pcc.unit_name THEN 1.0
                 WHEN similarity(COALESCE(er.unit_name, ''), COALESCE(pcc.unit_name, '')) > 0.7
                      THEN similarity(er.unit_name, pcc.unit_name)
                 ELSE 0.0 END AS agency_match,
            CASE WHEN er.announce_date IS NOT NULL AND pcc.announce_date IS NOT NULL
                      AND ABS(er.announce_date - pcc.announce_date) <= 3 THEN 1.0
                 WHEN er.announce_date IS NOT NULL AND pcc.announce_date IS NOT NULL
                      AND ABS(er.announce_date - pcc.announce_date) <= 7 THEN 0.5
                 ELSE 0.0 END AS date_proximity
        FROM tender_records er
        CROSS JOIN LATERAL (
            SELECT pr.*, similarity(pr.title, er.title) AS sim
            FROM tender_records pr
            WHERE pr.source = 'pcc'
              AND pr.title % er.title
            ORDER BY similarity(pr.title, er.title) DESC
            LIMIT 1
        ) pcc
        WHERE er.id = :eid AND pcc.sim > 0.5
    """)

    result = await db.execute(sql, {"eid": ezbid_record_id})
    row = result.one_or_none()
    if not row:
        return None

    title_sim = float(row.title_sim)
    agency_match = float(row.agency_match)
    date_proximity = float(row.date_proximity)
    confidence = title_sim * 0.5 + agency_match * 0.3 + date_proximity * 0.2

    if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
        return None

    return {
        "ezbid_id": row.eid,
        "pcc_unit_id": row.pcc_unit_id,
        "pcc_job_number": row.pcc_job_number,
        "title_sim": title_sim,
        "agency_match": agency_match,
        "date_proximity": date_proximity,
        "confidence": confidence,
        "is_high": _passes_high_guard(title_sim, agency_match, date_proximity),
    }


def _passes_high_guard(
    title_sim: float,
    agency_match: float,
    date_proximity: float,
    ezbid_title: str = "",
    pcc_title: str = "",
) -> bool:
    """升級為**五重 guard**：避免 trigram false positive。

    Live apply 5/28 揭發：原三重 guard 對短字串仍 false positive：
    - 「30吋閘閥」對「30吋對銲長徑彎頭」title_sim=1.0 但不同物
    - 短字串 + 同前綴序列號（Danas-H-XX）pg_trgm 高 sim 但實際不同案

    新增第 4、5 重 guard：
    4. title 長度 ≥ 12 字（filter 短字串高 sim 風險）
    5. title 完全相同 (exact match) OR title_sim = 1.0 之外要求 length ≥ 20
    """
    if not (
        title_sim >= GUARD_TITLE_SIM
        and agency_match >= GUARD_AGENCY_SIM
        and date_proximity >= 1.0
    ):
        return False

    # 4. title 長度 guard（短字串 trigram 高 sim 但易誤判）
    e_clean = (ezbid_title or "").strip()
    p_clean = (pcc_title or "").strip()
    if len(e_clean) < 12 or len(p_clean) < 12:
        return False

    # 5. 強制 title exact match — 唯一安全保證
    # 長字串 (≥20) 共前綴仍可能 false positive（如「第56屆全國技能競賽OO職類」系列）
    # exact match 才 auto-link，其他都進 MEDIUM review queue
    if e_clean != p_clean:
        return False

    return True


async def apply_match_to_record(
    db: AsyncSession,
    ezbid_id: int,
    pcc_unit_id: str,
    pcc_job_number: str,
    confidence: float,
) -> bool:
    """寫入 4 個 pcc_match_* 欄位到指定 ezbid record。

    Returns: True if updated, False if not found.
    """
    result = await db.execute(
        text("""
            UPDATE tender_records
            SET pcc_match_unit_id = :uid,
                pcc_match_job_number = :jn,
                pcc_match_confidence = :conf,
                pcc_match_at = NOW()
            WHERE id = :eid
              AND source = 'ezbid'
        """),
        {"eid": ezbid_id, "uid": pcc_unit_id, "jn": pcc_job_number, "conf": confidence},
    )
    return result.rowcount > 0


async def enrich_all_unmatched(
    db: AsyncSession,
    batch_size: int = 500,
    high_only: bool = True,
    dry_run: bool = False,
) -> Dict[str, int]:
    """對所有未 match ezbid records 跑 enrichment。

    Args:
        batch_size: 每批處理大小（避 statement_timeout）
        high_only: True = 只 auto-link HIGH (≥0.85 + 三重 guard) / False = HIGH+MEDIUM
        dry_run: True = 不寫 DB，只回傳統計

    Returns:
        {scanned, matched_high, matched_medium, applied, skipped, errors}
    """
    stats = {
        "scanned": 0,
        "matched_high": 0,
        "matched_medium": 0,
        "applied": 0,
        "skipped": 0,
        "errors": 0,
    }

    # 找所有未 match 的 ezbid
    offset = 0
    while True:
        batch_sql = text(f"""
            SELECT
                er.id AS eid, er.title AS etitle, er.unit_name AS eunit,
                er.announce_date AS edate, er.ezbid_id,
                pcc.id AS pid, pcc.title AS ptitle, pcc.unit_name AS punit,
                pcc.announce_date AS pdate,
                pcc.unit_id AS pcc_unit_id, pcc.job_number AS pcc_job_number,
                pcc.sim AS title_sim,
                CASE WHEN er.unit_name = pcc.unit_name THEN 1.0
                     WHEN similarity(COALESCE(er.unit_name, ''), COALESCE(pcc.unit_name, '')) > 0.7
                          THEN similarity(er.unit_name, pcc.unit_name)
                     ELSE 0.0 END AS agency_match,
                CASE WHEN er.announce_date IS NOT NULL AND pcc.announce_date IS NOT NULL
                          AND ABS(er.announce_date - pcc.announce_date) <= 3 THEN 1.0
                     WHEN er.announce_date IS NOT NULL AND pcc.announce_date IS NOT NULL
                          AND ABS(er.announce_date - pcc.announce_date) <= 7 THEN 0.5
                     ELSE 0.0 END AS date_proximity
            FROM (
                SELECT * FROM tender_records
                WHERE source = 'ezbid'
                  AND title IS NOT NULL AND title != ''
                  AND pcc_match_unit_id IS NULL  -- 只跑還沒 match 的
                ORDER BY id
                OFFSET {offset} LIMIT {batch_size}
            ) er
            CROSS JOIN LATERAL (
                SELECT pr.*, similarity(pr.title, er.title) AS sim
                FROM tender_records pr
                WHERE pr.source = 'pcc'
                  AND pr.title % er.title
                ORDER BY similarity(pr.title, er.title) DESC
                LIMIT 1
            ) pcc
            WHERE pcc.sim > 0.5
        """)

        try:
            result = await db.execute(batch_sql)
            rows = result.fetchall()
        except Exception as e:
            logger.error(f"enrichment batch offset={offset} failed: {e}")
            stats["errors"] += 1
            break

        if not rows and offset >= 100:
            # 沒更多 batch（OFFSET 已 >= 100 但無 row → 停）
            break

        stats["scanned"] += batch_size

        for row in rows:
            title_sim = float(row.title_sim)
            agency = float(row.agency_match)
            date_prox = float(row.date_proximity)
            confidence = title_sim * 0.5 + agency * 0.3 + date_prox * 0.2

            if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
                stats["skipped"] += 1
                continue

            is_high = _passes_high_guard(
                title_sim, agency, date_prox,
                ezbid_title=row.etitle or "",
                pcc_title=row.ptitle or "",
            )

            if is_high:
                stats["matched_high"] += 1
            else:
                stats["matched_medium"] += 1

            # 只 auto-link HIGH（high_only=True 時）
            if high_only and not is_high:
                stats["skipped"] += 1
                continue

            if not dry_run:
                ok = await apply_match_to_record(
                    db, row.eid, row.pcc_unit_id, row.pcc_job_number, confidence
                )
                if ok:
                    stats["applied"] += 1
                else:
                    stats["errors"] += 1

        offset += batch_size

        # 安全 limit：避免無窮迴圈（理論上 27k / 500 = 55 batches）
        if offset > 100000:
            logger.warning(f"enrichment offset limit hit: {offset}")
            break

    if not dry_run:
        await db.commit()

    return stats
