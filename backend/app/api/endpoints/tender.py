"""
標案檢索 API 端點 (POST-only)

提供政府電子採購網標案搜尋、詳情查詢、廠商搜尋、智能推薦。

Version: 1.0.0
"""
from typing import Optional, List
from pydantic import BaseModel, Field

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tender_search_service import TenderSearchService
from app.schemas.common import SuccessResponse
from app.db.database import get_async_db as get_db

router = APIRouter(prefix="/tender", tags=["標案檢索"])


# ============================================================================
# Schemas
# ============================================================================

class TenderSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100, description="搜尋關鍵字")
    page: int = Field(1, ge=1, le=100)
    category: Optional[str] = Field(None, description="分類: 工程/勞務/財物")
    search_type: Optional[str] = Field("title", description="搜尋模式: title/org/company")


class TenderDetailRequest(BaseModel):
    unit_id: str = Field(..., description="機關代碼")
    job_number: str = Field(..., description="標案案號")


class TenderCompanySearchRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=100)
    page: int = Field(1, ge=1, le=100)


class TenderRecommendRequest(BaseModel):
    keywords: Optional[List[str]] = Field(None, description="自訂關鍵字 (空=使用預設)")
    page: int = Field(1, ge=1)


# ============================================================================
# Dependencies
# ============================================================================

def get_tender_service() -> TenderSearchService:
    """取得標案搜尋服務 (含 Redis 快取)"""
    try:
        from app.core.redis_client import get_redis_client
        redis = get_redis_client()
    except Exception:
        redis = None
    return TenderSearchService(redis_client=redis)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/search")
async def search_tenders(
    req: TenderSearchRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """搜尋標案 — g0v + ezbid 雙軌合併 (預設近 30 天)"""
    from datetime import datetime, timedelta

    if req.search_type == "org":
        result = await service.search_by_org(req.query, page=req.page)
    elif req.search_type == "company":
        result = await service.search_by_company(req.query, page=req.page)
    else:
        result = await service.search_by_title(
            query=req.query, page=req.page, category=req.category,
        )

    # 搜尋模式不強制 30 天篩選 (推薦模式才篩選)

    # 合併 ezbid 即時資料 (僅第一頁)
    if req.page in (None, 1):
        try:
            from app.services.ezbid_scraper import EzbidScraper
            scraper = EzbidScraper()
            category_map = {"工程": "WORK", "勞務": "SERV", "財物": "PPTY"}
            cat = category_map.get(req.category or "", "ALL")
            ezbid = await scraper.fetch_latest(query=req.query, category=cat, pages=1)

            seen = {(r.get("unit_id", "") + r.get("title", "")[:20]) for r in result.get("records", [])}
            ezbid_added = 0
            for r in ezbid.get("records", []):
                key = r.get("ezbid_id", "") + r.get("title", "")[:20]
                if key not in seen:
                    seen.add(key)
                    result["records"].insert(0, {
                        "date": r.get("date", ""),
                        "raw_date": int(r.get("date", "0").replace("-", "")) if r.get("date") else 0,
                        "title": r.get("title", ""),
                        "type": r.get("type", ""),
                        "category": r.get("category", ""),
                        "unit_id": r.get("ezbid_id", ""),
                        "unit_name": r.get("unit_name", ""),
                        "job_number": "",
                        "company_names": [], "company_ids": [],
                        "winner_names": [], "bidder_names": [],
                        "tender_api_url": r.get("ezbid_url", ""),
                        "source": "ezbid",
                    })
                    ezbid_added += 1

            if ezbid_added > 0:
                result["records"].sort(key=lambda x: x.get("raw_date", 0), reverse=True)
                result["total_records"] = result.get("total_records", 0) + ezbid_added
        except Exception:
            pass  # ezbid 失敗不影響主搜尋

    return SuccessResponse(data=result)


@router.post("/detail")
async def get_tender_detail(
    req: TenderDetailRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """取得標案詳情 (含歷次公告)"""
    result = await service.get_tender_detail(
        unit_id=req.unit_id, job_number=req.job_number,
    )
    if not result:
        return SuccessResponse(data=None, message="查無此標案")
    return SuccessResponse(data=result)


@router.post("/detail-full")
async def get_tender_detail_full(
    req: TenderDetailRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """標案完整戰情 — 詳情 + 相似標案 + 機關生態 + 競爭對手 (並行)"""
    import asyncio
    from app.services.tender_analytics_service import TenderAnalyticsService

    analytics = TenderAnalyticsService()

    # Step 1: 取得詳情 (需先知道機關名稱)
    detail = await service.get_tender_detail(req.unit_id, req.job_number)
    if not detail:
        return SuccessResponse(data=None, message="查無此標案")

    agency_name = detail.get("unit_name", "")

    # Step 2: 並行取得戰情+底價+機關生態 (傳入 detail 避免重複查詢)
    from app.services.tender_analytics_battle import battle_room as _battle_room
    battle_task = _battle_room(service, req.unit_id, req.job_number, detail=detail)
    from app.services.tender_analytics_price import price_analysis as _price_analysis
    price_task = _price_analysis(service, req.unit_id, req.job_number, detail=detail)
    async def _empty_org(): return {}
    org_task = analytics.org_ecosystem(agency_name, pages=3) if agency_name else _empty_org()

    results = await asyncio.gather(battle_task, price_task, org_task, return_exceptions=True)

    battle = results[0] if not isinstance(results[0], Exception) else {}
    price = results[1] if not isinstance(results[1], Exception) else {}
    org_eco = results[2] if not isinstance(results[2], Exception) else {}

    # 從相似標案推估決標折率
    estimate = None
    if battle.get("similar_tenders") and price and not price.get("error"):
        budget_val = price.get("prices", {}).get("budget")
        if budget_val and not price.get("prices", {}).get("award_amount"):
            # 取相似標案的決標資料計算歷史折率
            import re
            ratios = []
            for st in battle.get("similar_tenders", []):
                try:
                    st_detail = await service.get_tender_detail(st.get("unit_id", ""), st.get("job_number", ""))
                    if not st_detail:
                        continue
                    for evt in st_detail.get("events", []):
                        ad = evt.get("award_details") or {}
                        ed = evt.get("detail") or {}
                        b_raw = ed.get("budget", "")
                        b = float(re.sub(r'[^\d.]', '', str(b_raw).replace(',', ''))) if b_raw else None
                        a = ad.get("total_award_amount")
                        if b and a and b > 0:
                            ratios.append(a / b)
                            break
                except Exception:
                    continue

            if ratios:
                avg_ratio = sum(ratios) / len(ratios)
                estimate = {
                    "avg_ratio": round(avg_ratio * 100, 1),
                    "sample_count": len(ratios),
                    "estimated_award": round(budget_val * avg_ratio),
                    "budget": budget_val,
                }

    return SuccessResponse(data={
        "detail": detail,
        "battle_room": battle,
        "org_ecosystem": org_eco,
        "price_analysis": price if not price.get("error") else None,
        "price_estimate": estimate,
    })


@router.post("/search-company")
async def search_by_company(
    req: TenderCompanySearchRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """依廠商名稱搜尋得標紀錄"""
    result = await service.search_by_company(
        company_name=req.company_name, page=req.page,
    )
    return SuccessResponse(data=result)


@router.post("/recommend")
async def recommend_tenders(
    req: TenderRecommendRequest,
    service: TenderSearchService = Depends(get_tender_service),
    db: AsyncSession = Depends(get_db),
):
    """智能推薦 — 訂閱關鍵字驅動 + ezbid 今日最新 (分區)"""
    from app.extended.models.tender import TenderSubscription

    # 1. 取得訂閱關鍵字 (優先) 或使用預設
    sub_keywords = req.keywords
    if not sub_keywords:
        subs = await db.execute(
            select(TenderSubscription)
            .where(TenderSubscription.is_active == True)  # noqa: E712
            .order_by(TenderSubscription.last_count.desc())
            .limit(5)
        )
        sub_list = subs.scalars().all()
        sub_keywords = [s.keyword for s in sub_list] if sub_list else None

    # 2. 並行取得: g0v 推薦 + ezbid 關鍵字 + ezbid 最新
    import asyncio
    from app.services.ezbid_scraper import EzbidScraper
    scraper = EzbidScraper()

    g0v_task = service.recommend_tenders(keywords=sub_keywords, page=req.page)
    async def _empty(): return {"records": []}
    ezbid_kw_task = scraper.fetch_for_keywords(sub_keywords[:3]) if sub_keywords else _empty()
    ezbid_latest_task = scraper.fetch_latest(pages=1, per_page=15)

    results = await asyncio.gather(g0v_task, ezbid_kw_task, ezbid_latest_task, return_exceptions=True)
    g0v_result = results[0] if not isinstance(results[0], Exception) else {"records": [], "keywords": []}
    ezbid_kw_result = results[1] if not isinstance(results[1], Exception) else {"records": []}
    ezbid_latest_result = results[2] if not isinstance(results[2], Exception) else {"records": []}

    def to_record(r):
        return {
            "date": r.get("date", ""),
            "raw_date": int(r.get("date", "0").replace("-", "")) if r.get("date") else 0,
            "title": r.get("title", ""),
            "type": r.get("type", ""),
            "category": r.get("category", ""),
            "unit_id": r.get("ezbid_id", ""),
            "unit_name": r.get("unit_name", ""),
            "job_number": "",
            "company_names": [], "company_ids": [],
            "winner_names": [], "bidder_names": [],
            "tender_api_url": r.get("ezbid_url", ""),
            "source": "ezbid",
        }

    # 合併業務推薦
    business_records = list(g0v_result.get("records", []))
    seen_titles = {r.get("title", "")[:20] for r in business_records}
    for r in ezbid_kw_result.get("records", []):
        key = r.get("title", "")[:20]
        if key not in seen_titles:
            seen_titles.add(key)
            rec = to_record(r)
            rec["matched_keyword"] = r.get("matched_keyword", "")
            business_records.append(rec)
    business_records.sort(key=lambda x: x.get("raw_date", 0), reverse=True)

    # 今日最新
    today_records = []
    for r in ezbid_latest_result.get("records", []):
        key = r.get("title", "")[:20]
        if key not in seen_titles:
            seen_titles.add(key)
            today_records.append(to_record(r))

    # 4. 篩選近 30 天
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    business_records = [r for r in business_records if (r.get("date") or "9999") >= cutoff]
    today_records = [r for r in today_records if (r.get("date") or "9999") >= cutoff]

    return SuccessResponse(data={
        "keywords": g0v_result.get("keywords", []),
        "total": len(business_records) + len(today_records),
        "today_records": today_records,
        "records": business_records,
    })


class TenderGraphRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    max_tenders: int = Field(20, ge=1, le=50)


@router.post("/graph")
async def get_tender_graph(
    req: TenderGraphRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """標案知識圖譜 — 機關→標案→廠商 關係網絡"""
    result = await service.build_tender_graph(
        query=req.query, max_tenders=req.max_tenders,
    )
    return SuccessResponse(data=result)


class TenderCreateCaseRequest(BaseModel):
    """從標案建立 PM Case"""
    unit_id: str = Field(..., description="機關代碼")
    job_number: str = Field(..., description="標案案號")
    title: str = Field(..., description="標案名稱")
    unit_name: str = Field("", description="招標機關名稱")
    budget: Optional[str] = Field(None, description="預算金額")
    category: Optional[str] = Field(None, description="分類")


@router.post("/create-case")
async def create_case_from_tender(
    req: TenderCreateCaseRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """從標案一鍵建立 PM Case + ERP Quotation"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.database import get_async_db as get_db
    from app.services.case_code_service import CaseCodeService
    from app.extended.models.pm import PMCase
    from app.extended.models.erp import ERPQuotation
    from app.db.database import AsyncSessionLocal
    import re
    from datetime import date

    async with AsyncSessionLocal() as db:
        # 防呆：檢查是否已建過此標案
        from sqlalchemy import select as sa_select
        existing = (await db.execute(
            sa_select(PMCase).where(
                PMCase.notes.ilike(f"%{req.job_number}%")
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"此標案已建案: {existing.case_code} ({existing.case_name[:30]})"
            )

        code_service = CaseCodeService(db)

        # 解析預算金額
        budget_amount = 0
        if req.budget:
            nums = re.sub(r'[^\d.]', '', req.budget.replace(',', ''))
            budget_amount = int(float(nums)) if nums else 0

        year = date.today().year

        # 產生案號
        case_code = await code_service.generate_case_code("pm", year, "01")

        # 查找或建立委託單位 (招標機關)
        client_vendor_id = None
        if req.unit_name:
            from app.extended.models.core import PartnerVendor
            from sqlalchemy import select as sa_select
            existing_client = (await db.execute(
                sa_select(PartnerVendor).where(
                    PartnerVendor.vendor_name == req.unit_name,
                    PartnerVendor.vendor_type == 'client',
                )
            )).scalar_one_or_none()
            if existing_client:
                client_vendor_id = existing_client.id
            else:
                new_client = PartnerVendor(
                    vendor_name=req.unit_name,
                    vendor_type='client',
                    notes=f"[標案自動建立] {req.job_number}",
                )
                db.add(new_client)
                await db.flush()
                client_vendor_id = new_client.id

        # 建立 PM Case
        pm_case = PMCase(
            case_code=case_code,
            case_name=req.title,
            year=year,
            status="bidding",
            contract_amount=budget_amount if budget_amount > 0 else None,
            client_vendor_id=client_vendor_id,
            notes=f"來源: 政府標案 {req.job_number} ({req.unit_name})",
        )
        db.add(pm_case)
        await db.flush()

        # 邀標階段不建立 ERP Quotation — 等確認投標後再建
        await db.commit()

        return SuccessResponse(data={
            "case_code": case_code,
            "pm_case_id": pm_case.id,
            "message": f"已建立案件 {case_code}",
        })


# ============================================================================
# Phase 3: 訂閱 + 書籤
# ============================================================================

class SubscriptionCreateRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = None
    notify_line: bool = True
    notify_system: bool = True


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


class SubscriptionUpdateRequest(BaseModel):
    id: int
    keyword: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    notify_line: Optional[bool] = None
    notify_system: Optional[bool] = None


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


@router.post("/realtime")
async def realtime_tenders(req: TenderSearchRequest):
    """即時標案 — 爬取 ezbid.tw 最新資料 (補充 PCC API 延遲)"""
    from app.services.ezbid_scraper import EzbidScraper

    category_map = {"工程": "WORK", "勞務": "SERV", "財物": "PPTY"}
    cat = category_map.get(req.category or "", "ALL")

    try:
        from app.core.redis_client import get_redis_client
        redis = get_redis_client()
    except Exception:
        redis = None

    scraper = EzbidScraper(redis_client=redis)
    result = await scraper.fetch_latest(query=req.query, category=cat, pages=1)
    return SuccessResponse(data=result)


@router.post("/check-subscriptions")
async def check_subscriptions(db: AsyncSession = Depends(get_db)):
    """手動觸發訂閱檢查 (也可由排程器自動呼叫)"""
    from app.services.tender_subscription_scheduler import check_all_subscriptions
    result = await check_all_subscriptions(db)
    return SuccessResponse(data=result)


# ============================================================================
# 廠商關注 (Company Bookmarks)
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


# ============================================================================
# Analytics — 標案分析
# ============================================================================

@router.post("/analytics/dashboard")
async def analytics_dashboard(request: Request):
    """招標採購儀表板 — 近期統計+類別分布+推薦標案"""
    from app.services.tender_analytics_service import TenderAnalyticsService
    body = await request.json() if request.headers.get("content-length", "0") != "0" else {}
    keywords = body.get("keywords")
    svc = TenderAnalyticsService()
    result = await svc.dashboard(keywords=keywords)
    return SuccessResponse(data=result)


@router.post("/analytics/battle-room")
async def analytics_battle_room(request: Request):
    """投標戰情室 — 相似標案+競爭對手分析"""
    from app.services.tender_analytics_service import TenderAnalyticsService
    body = await request.json()
    unit_id = body.get("unit_id")
    job_number = body.get("job_number")
    if not unit_id or not job_number:
        raise HTTPException(status_code=400, detail="unit_id 和 job_number 為必填")
    svc = TenderAnalyticsService()
    result = await svc.battle_room(unit_id=unit_id, job_number=job_number)
    return SuccessResponse(data=result)


@router.post("/analytics/org-ecosystem")
async def analytics_org_ecosystem(request: Request):
    """機關生態分析 — 歷年標案+得標廠商分布"""
    from app.services.tender_analytics_service import TenderAnalyticsService
    body = await request.json()
    org_name = body.get("org_name")
    if not org_name:
        raise HTTPException(status_code=400, detail="org_name 為必填")
    try:
        svc = TenderAnalyticsService()
        result = await svc.org_ecosystem(org_name=org_name, pages=body.get("pages", 3))
        import json as _json
        return JSONResponse(content={"success": True, "data": result},
                            media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"org-ecosystem error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/analytics/company-profile")
async def analytics_company_profile(request: Request):
    """廠商分析 — 得標歷史+機關分布+勝率"""
    from app.services.tender_analytics_service import TenderAnalyticsService
    body = await request.json()
    company_name = body.get("company_name")
    if not company_name:
        raise HTTPException(status_code=400, detail="company_name 為必填")
    try:
        svc = TenderAnalyticsService()
        result = await svc.company_profile(company_name=company_name, pages=body.get("pages", 3))
        return JSONResponse(content={"success": True, "data": result},
                            media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"company-profile error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/analytics/price-analysis")
async def tender_price_analysis(request: Request):
    """底價分析 — 單一標案的預算/底價/決標金額比較"""
    from app.services.tender_analytics_service import TenderAnalyticsService
    body = await request.json()
    unit_id = body.get("unit_id")
    job_number = body.get("job_number")
    if not unit_id or not job_number:
        raise HTTPException(status_code=400, detail="unit_id 和 job_number 為必填")
    try:
        svc = TenderAnalyticsService()
        result = await svc.price_analysis(unit_id=unit_id, job_number=job_number)
        return JSONResponse(content={"success": True, "data": result},
                            media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"price-analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/analytics/price-trends")
async def tender_price_trends(request: Request):
    """價格趨勢 — 同類標案的價格統計與分布"""
    from app.services.tender_analytics_service import TenderAnalyticsService
    body = await request.json()
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="query 為必填")
    try:
        svc = TenderAnalyticsService()
        result = await svc.price_trends(query=query, pages=body.get("pages", 3))
        return JSONResponse(content={"success": True, "data": result},
                            media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"price-trends error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])
