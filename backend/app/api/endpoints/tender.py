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
    """搜尋標案 (依標題關鍵字)"""
    result = await service.search_by_title(
        query=req.query, page=req.page, category=req.category,
    )
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
):
    """智能推薦 — 依乾坤核心業務關鍵字推薦相關標案"""
    result = await service.recommend_tenders(
        keywords=req.keywords, page=req.page,
    )
    return SuccessResponse(data=result)


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
    return SuccessResponse(data=[{
        "id": s.id, "keyword": s.keyword, "category": s.category,
        "is_active": s.is_active, "notify_line": s.notify_line,
        "notify_system": s.notify_system,
        "last_checked_at": str(s.last_checked_at) if s.last_checked_at else None,
        "last_count": s.last_count,
    } for s in items])


@router.post("/subscriptions/create")
async def create_subscription(
    req: SubscriptionCreateRequest, db: AsyncSession = Depends(get_db),
):
    """建立訂閱"""
    from app.extended.models.tender import TenderSubscription
    sub = TenderSubscription(
        keyword=req.keyword, category=req.category,
        notify_line=req.notify_line, notify_system=req.notify_system,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return SuccessResponse(data={"id": sub.id, "keyword": sub.keyword})


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
    if "status" in req: bookmark.status = req["status"]
    if "case_code" in req: bookmark.case_code = req["case_code"]
    if "notes" in req: bookmark.notes = req["notes"]
    await db.commit()
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
