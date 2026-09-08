# -*- coding: utf-8 -*-
"""案件金流異常 API（POST-only，同本專案慣例）

owner 2026-09-08：「是否異常案件標註機制並增列篩選查詢，
以利解除或處理異常費用之案件機制」。

判準與「為什麼異常是推導的」見 `app/services/erp/finance_anomaly.py`。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_auth
from app.db.database import get_async_db
from app.schemas.common import SuccessResponse
from app.services.erp import finance_anomaly

router = APIRouter()


class AnomalyListRequest(BaseModel):
    #: 只列還沒有人判讀的（待處理清單）。預設 False ＝連已判讀的一起列，
    #: 因為「已判讀」不代表數字變正常了。
    only_open: bool = False
    codes: Optional[list[str]] = None
    year: Optional[int] = Field(None, description="案件年度（西元，見 §2.5）")


class AnomalyAckRequest(BaseModel):
    quotation_id: int
    anomaly_type: str
    #: 必填且不得只是空白 —— 沒有原因的判讀等於把問題藏起來。
    reason: str = Field(..., min_length=2, max_length=500)


class AnomalyUnackRequest(BaseModel):
    quotation_id: int
    anomaly_type: str


@router.post("/types")
async def list_types(_: object = Depends(require_auth())):
    """判準清單 —— 前端的篩選選項由後端下發，不在前端手抄一份。"""
    return SuccessResponse(data=[
        {"code": a.code, "label": a.label, "severity": a.severity, "explain": a.explain}
        for a in finance_anomaly.ANOMALY_TYPES
    ])


@router.post("/list")
async def list_anomalies(
    req: AnomalyListRequest,
    db: AsyncSession = Depends(get_async_db),
    _: object = Depends(require_auth()),
):
    """異常案件清單（含案號、案名、判讀狀態）。"""
    found = await finance_anomaly.scan(db, codes=req.codes)
    if not found:
        return SuccessResponse(data={"items": [], "total": 0, "open_total": 0})

    acks = await finance_anomaly.load_acks(db, list(found))
    rows = (await db.execute(
        text("SELECT id, case_code, case_name, total_price, year "
             "FROM erp_quotations WHERE id = ANY(:ids)"),
        {"ids": list(found)},
    )).all()
    meta = {int(r[0]): r for r in rows}

    items = []
    for qid, anomalies in found.items():
        m = meta.get(qid)
        if m is None:
            continue
        # 年度篩選走**案件年度**（西元）——同 §2.5，後端不做 +1911。
        if req.year is not None and m[4] is not None and int(m[4]) != int(req.year):
            continue
        enriched = []
        for a in anomalies:
            ack = acks.get((qid, a["code"]))
            enriched.append({**a, "acknowledged": ack is not None, "ack": ack})
        items.append({
            "quotation_id": qid,
            "case_code": m[1],
            "case_name": m[2],
            "total_price": float(m[3]) if m[3] is not None else None,
            "year": m[4],
            "anomalies": enriched,
            "open_count": sum(1 for a in enriched if not a["acknowledged"]),
        })
    items.sort(key=lambda x: (-x["open_count"], x["case_code"] or ""))
    if req.only_open:
        items = [i for i in items if i["open_count"] > 0]
    return SuccessResponse(data={
        "items": items,
        "total": len(items),
        "open_total": sum(1 for i in items if i["open_count"] > 0),
    })


@router.post("/ack")
async def ack_anomaly(
    req: AnomalyAckRequest,
    db: AsyncSession = Depends(get_async_db),
    user: object = Depends(require_auth()),
):
    """判讀一筆異常（＝解除待辦，不改任何金額）。"""
    if req.anomaly_type not in finance_anomaly.BY_CODE:
        raise HTTPException(400, f"未知的異常類型：{req.anomaly_type}")
    who = getattr(user, "full_name", None) or getattr(user, "username", None) or "unknown"
    await db.execute(text("""
        INSERT INTO erp_finance_anomaly_acks (quotation_id, anomaly_type, reason, acked_by)
        VALUES (:qid, :t, :reason, :who)
        ON CONFLICT (quotation_id, anomaly_type)
        DO UPDATE SET reason = EXCLUDED.reason, acked_by = EXCLUDED.acked_by, acked_at = NOW()
    """), {"qid": req.quotation_id, "t": req.anomaly_type,
           "reason": req.reason.strip(), "who": who})
    await db.commit()
    return SuccessResponse(data={"quotation_id": req.quotation_id,
                                 "anomaly_type": req.anomaly_type},
                           message="已記錄判讀")


@router.post("/unack")
async def unack_anomaly(
    req: AnomalyUnackRequest,
    db: AsyncSession = Depends(get_async_db),
    _: object = Depends(require_auth()),
):
    """撤銷判讀 —— 判錯了要能退回待處理，否則只剩「再判一次」這條路。"""
    await db.execute(text(
        "DELETE FROM erp_finance_anomaly_acks "
        "WHERE quotation_id = :qid AND anomaly_type = :t"),
        {"qid": req.quotation_id, "t": req.anomaly_type})
    await db.commit()
    return SuccessResponse(data={"quotation_id": req.quotation_id}, message="已退回待處理")
