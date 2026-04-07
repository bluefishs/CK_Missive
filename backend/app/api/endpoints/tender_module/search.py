"""
標案搜尋 API — search / detail / detail-full / search-company / recommend / realtime
"""
from typing import Optional, List
from pydantic import BaseModel, Field

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tender_search_service import TenderSearchService
from app.schemas.common import SuccessResponse
from app.db.database import get_async_db as get_db

logger = logging.getLogger(__name__)

router = APIRouter()


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
