"""
標案訂閱 + 書籤 + 廠商關注 API
"""
from typing import Optional
from pydantic import BaseModel, Field

import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import SuccessResponse
from app.db.database import get_async_db as get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class SubscriptionCreateRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = None
    notify_line: bool = True
    notify_system: bool = True


class SubscriptionUpdateRequest(BaseModel):
    id: int
    keyword: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    notify_line: Optional[bool] = None
    notify_system: Optional[bool] = None


class BookmarkCreateRequest(BaseModel):
    unit_id: str
    job_number: str
    title: str
    unit_name: Optional[str] = None
    budget: Optional[str] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None


class BookmarkUpdateRequest(BaseModel):
    status: Optional[str] = None
    case_code: Optional[str] = None
    notes: Optional[str] = None


# ============================================================================
# Subscription Endpoints
# ============================================================================

@router.post("/subscriptions/list")
async def list_subscriptions(db: AsyncSession = Depends(get_db)):
    """列出所有訂閱"""
    from app.extended.models.tender import TenderSubscription
    result = await db.execute(
        select(TenderSubscription).order_by(TenderSubscription.created_at.desc())
    )
    items = result.scalars().all()
    import json as _json
    return SuccessResponse(data=[{
        "id": s.id, "keyword": s.keyword, "category": s.category,
        "is_active": s.is_active, "notify_line": s.notify_line,
        "notify_system": s.notify_system,
        "last_checked_at": str(s.last_checked_at) if s.last_checked_at else None,
        "last_count": s.last_count,
        "last_diff": getattr(s, 'last_diff', 0) or 0,
        "last_new_titles": _json.loads(s.last_new_titles) if getattr(s, 'last_new_titles', None) else [],
    } for s in items])


@router.post("/subscriptions/create")
async def create_subscription(
    req: SubscriptionCreateRequest, db: AsyncSession = Depends(get_db),
):
    """建立訂閱 — 建立後立即執行一次查詢"""
    from datetime import datetime
    from app.extended.models.tender import TenderSubscription
    from app.services.tender_search_service import TenderSearchService

    sub = TenderSubscription(
        keyword=req.keyword, category=req.category,
        notify_line=req.notify_line, notify_system=req.notify_system,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    # 建立後立即查詢一次，更新 last_checked_at + last_new_titles
    try:
        import json as _json
        service = TenderSearchService()
        result = await service.search_by_title(query=req.keyword, page=1, category=req.category)
        sub.last_checked_at = datetime.utcnow()
        sub.last_count = result.get("total_records", 0)
        # 去重後取前 5 筆標題
        seen_t = set()
        titles = []
        for r in result.get("records", [])[:15]:
            t = r.get("title", "")[:80] if isinstance(r, dict) else ""
            if t and t not in seen_t:
                seen_t.add(t)
                titles.append(t)
                if len(titles) >= 5:
                    break
        sub.last_new_titles = _json.dumps(titles, ensure_ascii=False) if titles else None
        await db.commit()
    except Exception:
        pass

    return SuccessResponse(data={"id": sub.id, "keyword": sub.keyword})


@router.post("/subscriptions/update")
async def update_subscription(
    req: SubscriptionUpdateRequest, db: AsyncSession = Depends(get_db),
):
    """更新訂閱"""
    from app.extended.models.tender import TenderSubscription

    result = await db.execute(
        select(TenderSubscription).where(TenderSubscription.id == req.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return SuccessResponse(success=False, message="訂閱不存在")

    if req.keyword is not None:
        sub.keyword = req.keyword
    if req.category is not None:
        sub.category = req.category if req.category else None
    if req.is_active is not None:
        sub.is_active = req.is_active
    if req.notify_line is not None:
        sub.notify_line = req.notify_line
    if req.notify_system is not None:
        sub.notify_system = req.notify_system

    await db.commit()
    await db.refresh(sub)

    return SuccessResponse(data={
        "id": sub.id, "keyword": sub.keyword,
        "category": sub.category, "is_active": sub.is_active,
    })


@router.post("/subscriptions/delete")
async def delete_subscription(
    req: BaseModel, db: AsyncSession = Depends(get_db),
):
    """刪除訂閱"""
    from app.extended.models.tender import TenderSubscription

    class IdReq(BaseModel):
        id: int
    parsed = IdReq.model_validate(req.model_dump() if hasattr(req, 'model_dump') else {})
    await db.execute(delete(TenderSubscription).where(TenderSubscription.id == parsed.id))
    await db.commit()
    return SuccessResponse(data={"deleted": True})


# ============================================================================
# Bookmark Endpoints
# ============================================================================

@router.post("/bookmarks/list")
async def list_bookmarks(db: AsyncSession = Depends(get_db)):
    """列出所有書籤"""
    from app.extended.models.tender import TenderBookmark
    result = await db.execute(
        select(TenderBookmark).order_by(TenderBookmark.created_at.desc())
    )
    items = result.scalars().all()
    return SuccessResponse(data=[{
        "id": b.id, "unit_id": b.unit_id, "job_number": b.job_number,
        "title": b.title, "unit_name": b.unit_name, "budget": b.budget,
        "deadline": b.deadline, "status": b.status, "case_code": b.case_code,
        "notes": b.notes,
        "created_at": str(b.created_at) if b.created_at else None,
    } for b in items])


@router.post("/bookmarks/create")
async def create_bookmark(
    req: BookmarkCreateRequest, db: AsyncSession = Depends(get_db),
):
    """收藏標案"""
    from app.extended.models.tender import TenderBookmark
    bookmark = TenderBookmark(
        unit_id=req.unit_id, job_number=req.job_number,
        title=req.title, unit_name=req.unit_name,
        budget=req.budget, deadline=req.deadline, notes=req.notes,
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)
    return SuccessResponse(data={"id": bookmark.id, "title": bookmark.title})


@router.post("/bookmarks/update")
async def update_bookmark(
    req: dict, db: AsyncSession = Depends(get_db),
):
    """更新書籤狀態"""
    from app.extended.models.tender import TenderBookmark
    bookmark_id = req.get("id")
    bookmark = (await db.execute(
        select(TenderBookmark).where(TenderBookmark.id == bookmark_id)
    )).scalar_one_or_none()
    if not bookmark:
        return SuccessResponse(data=None, message="書籤不存在")
    new_status = req.get("status")
    if "status" in req: bookmark.status = new_status
    if "case_code" in req: bookmark.case_code = req["case_code"]
    if "notes" in req: bookmark.notes = req["notes"]
    await db.commit()

    # If status changed to 'won', publish event
    if new_status == "won" and bookmark:
        try:
            from app.core.event_bus import EventBus
            from app.core.domain_events import tender_awarded
            bus = EventBus.get_instance()
            await bus.publish(tender_awarded(
                unit_id=bookmark.unit_id or "",
                job_number=bookmark.job_number or "",
                award_amount=0,  # Will be enriched later
            ))
        except Exception:
            pass

    return SuccessResponse(data={"id": bookmark.id, "status": bookmark.status})


@router.post("/bookmarks/delete")
async def delete_bookmark(req: dict, db: AsyncSession = Depends(get_db)):
    """刪除書籤"""
    from app.extended.models.tender import TenderBookmark
    await db.execute(delete(TenderBookmark).where(TenderBookmark.id == req.get("id")))
    await db.commit()
    return SuccessResponse(data={"deleted": True})


@router.post("/check-subscriptions")
async def check_subscriptions(db: AsyncSession = Depends(get_db)):
    """手動觸發訂閱檢查 (也可由排程器自動呼叫)"""
    from app.services.tender_subscription_scheduler import check_all_subscriptions
    result = await check_all_subscriptions(db)
    return SuccessResponse(data=result)


# ============================================================================
# Company Bookmarks (廠商關注)
# ============================================================================

@router.post("/companies/list")
async def list_company_bookmarks(db: AsyncSession = Depends(get_db)):
    """列出所有關注廠商"""
    from app.extended.models.tender import CompanyBookmark
    result = await db.execute(
        select(CompanyBookmark).order_by(CompanyBookmark.created_at.desc())
    )
    items = result.scalars().all()
    return SuccessResponse(data=[{
        "id": c.id, "company_name": c.company_name,
        "tag": c.tag, "notes": c.notes,
        "created_at": str(c.created_at) if c.created_at else None,
    } for c in items])


@router.post("/companies/add")
async def add_company_bookmark(request: Request, db: AsyncSession = Depends(get_db)):
    """加入關注廠商"""
    from app.extended.models.tender import CompanyBookmark
    body = await request.json()
    name = body.get("company_name", "").strip()
    if not name:
        return SuccessResponse(success=False, message="廠商名稱不可為空")

    existing = await db.execute(
        select(CompanyBookmark).where(CompanyBookmark.company_name == name)
    )
    if existing.scalar_one_or_none():
        return SuccessResponse(success=False, message="已關注此廠商")

    bm = CompanyBookmark(
        company_name=name,
        tag=body.get("tag", "competitor"),
        notes=body.get("notes"),
    )
    db.add(bm)
    await db.commit()
    await db.refresh(bm)
    return SuccessResponse(data={"id": bm.id, "company_name": bm.company_name})


@router.post("/companies/remove")
async def remove_company_bookmark(request: Request, db: AsyncSession = Depends(get_db)):
    """移除關注廠商"""
    from app.extended.models.tender import CompanyBookmark
    body = await request.json()
    company_id = body.get("id")
    if company_id:
        await db.execute(delete(CompanyBookmark).where(CompanyBookmark.id == company_id))
    else:
        name = body.get("company_name", "")
        await db.execute(delete(CompanyBookmark).where(CompanyBookmark.company_name == name))
    await db.commit()
    return SuccessResponse(data={"removed": True})
