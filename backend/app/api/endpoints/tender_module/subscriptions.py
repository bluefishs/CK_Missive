"""
標案訂閱 + 書籤 + 廠商關注 API
"""
import logging
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import SuccessResponse
from app.schemas.tender_admin import (
    BookmarkCreateRequest,
    BookmarkUpdateRequest,
    IdRequest,
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
)
from app.db.database import get_async_db as get_db
from app.core.dependencies import require_auth
from app.extended.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


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
    from app.services.tender.search import TenderSearchService

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
    req: IdRequest, db: AsyncSession = Depends(get_db),
):
    """刪除訂閱"""
    from app.extended.models.tender import TenderSubscription

    await db.execute(delete(TenderSubscription).where(TenderSubscription.id == req.id))
    await db.commit()
    return SuccessResponse(data={"deleted": True})


# ============================================================================
# Bookmark Endpoints
# ============================================================================

@router.post("/bookmarks/list")
async def list_bookmarks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth()),
):
    """列出當前用戶的書籤（per-user + alias group 展開）

    R4-2 (v6.9 / 2026-05-12)：alias_rls_audit step 21 揭發此處 user_id ==
    沒展開 alias group → 多帳號用戶看不到 alias 帳號的 bookmark。
    修法：用 expand_user_alias 展開到 alias group。
    """
    from app.extended.models.tender import TenderBookmark
    from app.services.user.alias import expand_user_alias

    alias_ids = await expand_user_alias(db, current_user.id)
    result = await db.execute(
        select(TenderBookmark)
        .where(TenderBookmark.user_id.in_(alias_ids))
        .order_by(TenderBookmark.created_at.desc())
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
    req: BookmarkCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth()),
):
    """收藏標案（綁定當前用戶，2026-04-24 起）"""
    from app.extended.models.tender import TenderBookmark
    # job_number 允許空字串（ezbid 案件）
    bookmark = TenderBookmark(
        user_id=current_user.id,
        unit_id=req.unit_id, job_number=req.job_number or "",
        title=req.title, unit_name=req.unit_name,
        budget=req.budget, deadline=req.deadline, notes=req.notes,
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)
    return SuccessResponse(data={"id": bookmark.id, "title": bookmark.title})


@router.post("/bookmarks/update")
async def update_bookmark(
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth()),
):
    """更新書籤狀態（限當前用戶或其 alias 的書籤）

    R4-2: alias group 內任一帳號的 bookmark 都應該能更新（同人）。
    """
    from app.extended.models.tender import TenderBookmark
    from app.services.user.alias import expand_user_alias

    alias_ids = await expand_user_alias(db, current_user.id)
    bookmark_id = req.get("id")
    bookmark = (await db.execute(
        select(TenderBookmark).where(
            TenderBookmark.id == bookmark_id,
            TenderBookmark.user_id.in_(alias_ids),
        )
    )).scalar_one_or_none()
    if not bookmark:
        return SuccessResponse(data=None, message="書籤不存在或非本人擁有")
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
async def delete_bookmark(
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth()),
):
    """刪除書籤（限當前用戶或其 alias 的書籤）

    R4-2: alias group 內任一帳號的 bookmark 都應該能刪除（同人）。
    """
    from app.extended.models.tender import TenderBookmark
    from app.services.user.alias import expand_user_alias

    alias_ids = await expand_user_alias(db, current_user.id)
    await db.execute(delete(TenderBookmark).where(
        TenderBookmark.id == req.get("id"),
        TenderBookmark.user_id.in_(alias_ids),
    ))
    await db.commit()
    return SuccessResponse(data={"deleted": True})


@router.post("/check-subscriptions")
async def check_subscriptions(db: AsyncSession = Depends(get_db)):
    """手動觸發訂閱檢查 (也可由排程器自動呼叫)"""
    from app.services.tender.subscription_scheduler import check_all_subscriptions
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


# ── 標案關鍵字規則（同義詞 + 排除）— owner 從「關鍵訂閱」UI 自維（L75.4，即時生效免 rebuild）──

class KeywordRulesRequest(BaseModel):
    synonyms: list = []      # 同義詞群組 [[主詞, 同義詞...], ...]
    exclusions: list = []    # 負面關鍵字 [str, ...]


@router.post("/keyword-rules/list")
async def get_keyword_rules(user: User = Depends(require_auth)):
    """取目前同義詞群組 + 排除關鍵字（給 UI 顯示）。"""
    from app.services.tender.business_recommendation import load_keyword_rules
    return SuccessResponse(data=load_keyword_rules())


@router.post("/keyword-rules/save")
async def save_keyword_rules(req: KeywordRulesRequest, user: User = Depends(require_auth)):
    """儲存同義詞 + 排除關鍵字 → 設定檔（持久 + 即時生效，不需 rebuild）。"""
    from app.services.tender.business_recommendation import save_keyword_rules as _save
    rules = _save(req.synonyms, req.exclusions)
    return SuccessResponse(data=rules)


@router.post("/keyword-rules/suggest")
async def suggest_keyword_rules(db: AsyncSession = Depends(get_db), user: User = Depends(require_auth)):
    """確定性 L3：從承攬史推導「公司職能工項」建議詞（詞頻），供 UI 一鍵加入。"""
    from app.services.tender.business_recommendation import suggest_keyword_terms
    return SuccessResponse(data=await suggest_keyword_terms(db))
