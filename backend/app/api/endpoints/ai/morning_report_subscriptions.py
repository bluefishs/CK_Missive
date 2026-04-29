"""
晨報訂閱 CRUD API — Morning Report Subscription 領域

從 ai_stats.py 抽出（領域驅動分治）。
純 CRUD，跟 AI/Stats 都無關 — 是 user × channel × sections 的訂閱配置。

端點:
- POST /ai/morning-report/subscriptions/list   — 列表
- POST /ai/morning-report/subscriptions/create — 建立
- POST /ai/morning-report/subscriptions/update — 更新
- POST /ai/morning-report/subscriptions/delete — 刪除
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import optional_auth, get_async_db

router = APIRouter()


class SubscriptionCreateRequest(BaseModel):
    channel: str = Field(..., description="telegram/line/discord/email")
    channel_recipient: str = Field(..., description="chat_id / user_id / email")
    display_name: Optional[str] = Field(None)
    sections: Optional[str] = Field("dispatch,meeting,site_visit,missing")
    handler_filter: Optional[str] = Field(None)
    user_id: Optional[int] = Field(None)


class SubscriptionUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    sections: Optional[str] = None
    handler_filter: Optional[str] = None
    enabled: Optional[bool] = None


@router.post("/morning-report/subscriptions/list")
async def list_subscriptions(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """晨報訂閱列表"""
    from app.extended.models import UserMorningReportSubscription

    rows = await db.execute(
        select(UserMorningReportSubscription)
        .order_by(UserMorningReportSubscription.id)
    )
    items = [
        {
            "id": r.id, "user_id": r.user_id, "display_name": r.display_name,
            "channel": r.channel, "channel_recipient": r.channel_recipient,
            "sections": r.sections, "handler_filter": r.handler_filter,
            "enabled": r.enabled,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows.scalars().all()
    ]
    return JSONResponse(
        {"success": True, "items": items, "total": len(items)},
        media_type="application/json; charset=utf-8",
    )


@router.post("/morning-report/subscriptions/create")
async def create_subscription(
    req: SubscriptionCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """建立晨報訂閱"""
    from app.extended.models import UserMorningReportSubscription

    sub = UserMorningReportSubscription(
        user_id=req.user_id,
        display_name=req.display_name,
        channel=req.channel,
        channel_recipient=req.channel_recipient,
        sections=req.sections or "dispatch,meeting,site_visit,missing",
        handler_filter=req.handler_filter,
        enabled=True,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return JSONResponse(
        {"success": True, "id": sub.id, "message": "訂閱已建立"},
        media_type="application/json; charset=utf-8",
    )


@router.post("/morning-report/subscriptions/update")
async def update_subscription(
    subscription_id: int,
    req: SubscriptionUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """更新晨報訂閱"""
    from app.extended.models import UserMorningReportSubscription

    sub = await db.execute(
        select(UserMorningReportSubscription)
        .where(UserMorningReportSubscription.id == subscription_id)
    )
    sub = sub.scalar_one_or_none()
    if not sub:
        return JSONResponse({"success": False, "error": "訂閱不存在"}, status_code=404)

    if req.display_name is not None:
        sub.display_name = req.display_name
    if req.sections is not None:
        sub.sections = req.sections
    if req.handler_filter is not None:
        sub.handler_filter = req.handler_filter
    if req.enabled is not None:
        sub.enabled = req.enabled
    await db.commit()
    return JSONResponse({"success": True, "message": "訂閱已更新"})


@router.post("/morning-report/subscriptions/delete")
async def delete_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(optional_auth()),
):
    """刪除晨報訂閱"""
    from app.extended.models import UserMorningReportSubscription

    result = await db.execute(
        delete(UserMorningReportSubscription)
        .where(UserMorningReportSubscription.id == subscription_id)
    )
    await db.commit()
    if result.rowcount == 0:
        return JSONResponse({"success": False, "error": "訂閱不存在"}, status_code=404)
    return JSONResponse({"success": True, "message": "訂閱已刪除"})
