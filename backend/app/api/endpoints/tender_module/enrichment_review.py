"""ADR-0046 task E：MEDIUM enrichment review queue API (L51, 2026-05-29)

對 enrichment _enqueue_medium_review 寫入的 1,293 筆 MEDIUM 候選提供
admin 列表 / approve / reject 介面。

- GET-style POST list: 分頁 + status filter
- approve: apply_match_to_record (寫 pcc_match_* 4 欄) + status=approved
- reject: 僅標 status=rejected（不 link）
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.database import get_async_db as get_db
from app.schemas.common import SuccessResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class ListReviewRequest(BaseModel):
    status: str = "pending"  # pending / approved / rejected / all
    limit: int = 50
    offset: int = 0
    min_confidence: Optional[float] = None  # filter by confidence threshold


class ReviewActionRequest(BaseModel):
    review_id: int
    note: Optional[str] = None


@router.post("/enrichment/review-queue/list")
async def list_review_queue(
    req: ListReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """列出 MEDIUM review queue（pending 預設）"""
    where_clauses = []
    params = {"limit": req.limit, "offset": req.offset}

    if req.status != "all":
        where_clauses.append("status = :status")
        params["status"] = req.status
    if req.min_confidence is not None:
        where_clauses.append("confidence >= :min_conf")
        params["min_conf"] = req.min_confidence

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    count_sql = text(f"SELECT COUNT(*) FROM tender_match_review {where_sql}")
    count_result = await db.execute(count_sql, params)
    total = count_result.scalar() or 0

    list_sql = text(f"""
        SELECT
            id, ezbid_record_id, pcc_unit_id, pcc_job_number,
            confidence, title_sim, agency_match, date_proximity,
            ezbid_title, pcc_title, ezbid_unit_name, pcc_unit_name,
            status, reviewed_by, reviewed_at, reviewer_note, created_at
        FROM tender_match_review
        {where_sql}
        ORDER BY confidence DESC, created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(list_sql, params)
    rows = result.mappings().all()

    items = [dict(r) for r in rows]
    for item in items:
        # datetime → str (Pydantic serialize)
        for k in ("reviewed_at", "created_at"):
            if item.get(k) is not None:
                item[k] = str(item[k])

    return SuccessResponse(data={
        "total": total,
        "items": items,
        "limit": req.limit,
        "offset": req.offset,
    })


@router.post("/enrichment/review-queue/approve")
async def approve_review(
    req: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin()),
):
    """approve 後寫 pcc_match_* 4 欄 + 標記 approved"""
    from app.services.tender.enrichment import apply_match_to_record

    # 取 review record
    r = await db.execute(
        text("""
            SELECT id, ezbid_record_id, pcc_unit_id, pcc_job_number,
                   confidence, status
            FROM tender_match_review WHERE id = :rid
        """),
        {"rid": req.review_id},
    )
    row = r.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="review item not found")

    if row["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"review item status={row['status']}, only 'pending' can be approved",
        )

    # 寫 pcc_match_* 4 欄
    ok = await apply_match_to_record(
        db, row["ezbid_record_id"], row["pcc_unit_id"], row["pcc_job_number"],
        row["confidence"],
    )
    if not ok:
        raise HTTPException(status_code=500, detail="apply_match_to_record failed")

    # 標 approved
    await db.execute(
        text("""
            UPDATE tender_match_review
            SET status = 'approved',
                reviewed_by = :uid,
                reviewed_at = NOW(),
                reviewer_note = :note
            WHERE id = :rid
        """),
        {"uid": current_user.id, "note": req.note, "rid": req.review_id},
    )
    await db.commit()

    logger.info(f"review approved: id={req.review_id} by user_id={current_user.id}")
    return SuccessResponse(data={"approved": True, "review_id": req.review_id})


@router.post("/enrichment/review-queue/reject")
async def reject_review(
    req: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin()),
):
    """reject 不 link，只標 rejected（後續同 ezbid×PCC pair 不會重複進 queue）"""
    r = await db.execute(
        text("SELECT id, status FROM tender_match_review WHERE id = :rid"),
        {"rid": req.review_id},
    )
    row = r.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="review item not found")

    if row["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"review item status={row['status']}, only 'pending' can be rejected",
        )

    await db.execute(
        text("""
            UPDATE tender_match_review
            SET status = 'rejected',
                reviewed_by = :uid,
                reviewed_at = NOW(),
                reviewer_note = :note
            WHERE id = :rid
        """),
        {"uid": current_user.id, "note": req.note, "rid": req.review_id},
    )
    await db.commit()

    logger.info(f"review rejected: id={req.review_id} by user_id={current_user.id}")
    return SuccessResponse(data={"rejected": True, "review_id": req.review_id})


@router.post("/enrichment/review-queue/stats")
async def review_queue_stats(db: AsyncSession = Depends(get_db)):
    """review queue 統計 — admin 看 backlog 大小 + 各 status 分布"""
    r = await db.execute(text("""
        SELECT status, COUNT(*) AS cnt,
               AVG(confidence) AS avg_conf,
               MIN(confidence) AS min_conf,
               MAX(confidence) AS max_conf
        FROM tender_match_review
        GROUP BY status
    """))
    rows = r.mappings().all()
    stats = {r["status"]: {
        "count": int(r["cnt"]),
        "avg_confidence": float(r["avg_conf"]) if r["avg_conf"] is not None else 0.0,
        "min_confidence": float(r["min_conf"]) if r["min_conf"] is not None else 0.0,
        "max_confidence": float(r["max_conf"]) if r["max_conf"] is not None else 0.0,
    } for r in rows}

    return SuccessResponse(data={
        "by_status": stats,
        "total": sum(s["count"] for s in stats.values()),
    })
