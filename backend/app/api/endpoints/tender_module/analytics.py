"""
標案分析 API — dashboard / battle-room / org-ecosystem / company-profile / price-analysis / price-trends
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.schemas.common import SuccessResponse
from app.db.database import get_async_db as get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analytics/cache-stats")
async def cache_stats(db: AsyncSession = Depends(get_db)):
    """標案快取 DB 統計"""
    from app.services.tender.cache import get_db_stats
    stats = await get_db_stats(db)
    return SuccessResponse(data=stats)


@router.post("/analytics/refresh-pending")
async def refresh_pending(db: AsyncSession = Depends(get_db)):
    """手動觸發：重查等標期標案的決標狀態"""
    from app.services.tender.cache import refresh_pending_tenders
    result = await refresh_pending_tenders(db, limit=30)
    return SuccessResponse(data=result)


@router.post("/analytics/cross-reference")
async def cross_reference(db: AsyncSession = Depends(get_db)):
    """跨服務索引：標記已建案標案 + 廠商正規化"""
    from app.services.tender.cache import cross_reference_pm_cases, normalize_company_names
    pm_result = await cross_reference_pm_cases(db)
    company_result = await normalize_company_names(db)
    return SuccessResponse(data={"pm_cases": pm_result, "companies": company_result})


# ============================================================================
# Endpoints
# ============================================================================

def _track_page_view(page: str) -> None:
    """L51 task F: page view counter (L31 ROI 治理)。failure-safe — metric 失敗不擋業務。"""
    try:
        from app.services.tender.metrics import get_tender_metrics
        get_tender_metrics().page_view.labels(page=page).inc()
    except Exception:
        pass


@router.post("/analytics/dashboard")
async def analytics_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """招標採購儀表板 — 近期統計+類別分布+推薦標案"""
    from app.services.tender.analytics import TenderAnalyticsService
    from app.services.tender.business_recommendation import (
        count_complete_tenders, fetch_complete_tenders,
    )
    body = await request.json() if request.headers.get("content-length", "0") != "0" else {}
    keywords = body.get("keywords")
    svc = TenderAnalyticsService()
    result = await svc.dashboard(keywords=keywords)

    # 2026-06-16 (owner 定案 Option A)：今日/本週「標案」數字改用 DB 同源去重口徑，
    #   與 /tender/search「今日最新」一致（fetch_complete_tenders SSOT）。
    #   根治原 live 爬蟲 stats 的兩大問題：①只抓今日→「本週」嚴重低估(544 vs 真實 ~8020)
    #   ②未去重/口徑不一。決標/得標廠商/無法決標等分卡維持 live 爬蟲（依舊）。
    try:
        stats = result.setdefault("stats", {})

        # 今日/本週標案（完整去重，含報價單，與 /tender/search 同源）
        today_count = await count_complete_tenders(db, days_back=0)
        week_count = await count_complete_tenders(db, days_back=6)
        stats["latest_bid"] = today_count
        stats["week_new_bid"] = week_count
        result["latest_bid_list"] = await fetch_complete_tenders(db, days_back=0, limit=500)
        result["week_new_bid_list"] = await fetch_complete_tenders(db, days_back=6, limit=500)
        result["today_total_count"] = today_count
        result["week_total_count"] = week_count

        # 決標（DB 新鮮資料，修 live 爬蟲「停留在 3 月」陳舊）：
        #   最新決標＝DB 最近決標日當日筆數；本週決標＝近 7 日；無法決標＝近 30 日。
        award_recent = await fetch_complete_tenders(db, days_back=30, limit=500, kind="award", order="date")
        latest_award_date = award_recent[0]["date"] if award_recent else ""
        latest_award_list = [r for r in award_recent if r["date"] == latest_award_date]
        stats["latest_award"] = len(latest_award_list)
        stats["week_new_award"] = await count_complete_tenders(db, days_back=6, kind="award")
        result["latest_award_list"] = latest_award_list
        result["week_new_award_list"] = await fetch_complete_tenders(db, days_back=6, limit=500, kind="award", order="date")

        # 無法決標（近 30 日，DB 同源）
        stats["failed_award"] = await count_complete_tenders(db, days_back=30, kind="failed")
        result["failed_award_list"] = await fetch_complete_tenders(db, days_back=30, limit=500, kind="failed", order="date")
    except Exception:
        # DB 覆寫失敗不擋主流程（退化為 live 爬蟲 stats）
        logger.warning("dashboard DB stats override failed (fallback to scrape)", exc_info=True)

    _track_page_view("dashboard")
    return SuccessResponse(data=result)


@router.post("/analytics/battle-room")
async def analytics_battle_room(request: Request):
    """投標戰情室 — 相似標案+競爭對手分析"""
    from app.services.tender.analytics import TenderAnalyticsService
    body = await request.json()
    unit_id = body.get("unit_id")
    job_number = body.get("job_number")
    if not unit_id or not job_number:
        raise HTTPException(status_code=400, detail="unit_id 和 job_number 為必填")
    svc = TenderAnalyticsService()
    result = await svc.battle_room(unit_id=unit_id, job_number=job_number)
    _track_page_view("battle_room")
    return SuccessResponse(data=result)


@router.post("/analytics/org-ecosystem")
async def analytics_org_ecosystem(request: Request):
    """機關生態分析 — 歷年標案+得標廠商分布"""
    from app.services.tender.analytics import TenderAnalyticsService
    body = await request.json()
    org_name = body.get("org_name")
    if not org_name:
        raise HTTPException(status_code=400, detail="org_name 為必填")
    try:
        svc = TenderAnalyticsService()
        result = await svc.org_ecosystem(org_name=org_name, pages=body.get("pages", 3))
        _track_page_view("org_ecosystem")
        import json as _json
        return JSONResponse(content={"success": True, "data": result},
                            media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"org-ecosystem error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="分析服務暫時無法使用")


@router.post("/analytics/company-profile")
async def analytics_company_profile(request: Request):
    """廠商分析 — 得標歷史+機關分布+勝率"""
    from app.services.tender.analytics import TenderAnalyticsService
    body = await request.json()
    company_name = body.get("company_name")
    if not company_name:
        raise HTTPException(status_code=400, detail="company_name 為必填")
    try:
        svc = TenderAnalyticsService()
        result = await svc.company_profile(company_name=company_name, pages=body.get("pages", 3))
        _track_page_view("company")
        return JSONResponse(content={"success": True, "data": result},
                            media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"company-profile error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="分析服務暫時無法使用")


@router.post("/analytics/price-analysis")
async def tender_price_analysis(request: Request):
    """底價分析 — 單一標案的預算/底價/決標金額比較"""
    from app.services.tender.analytics import TenderAnalyticsService
    body = await request.json()
    unit_id = body.get("unit_id")
    job_number = body.get("job_number")
    if not unit_id or not job_number:
        raise HTTPException(status_code=400, detail="unit_id 和 job_number 為必填")
    try:
        svc = TenderAnalyticsService()
        result = await svc.price_analysis(unit_id=unit_id, job_number=job_number)
        _track_page_view("price_analysis")
        return JSONResponse(content={"success": True, "data": result},
                            media_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"price-analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="分析服務暫時無法使用")


@router.post("/analytics/price-trends")
async def tender_price_trends(request: Request):
    """價格趨勢 — 同類標案的價格統計與分布"""
    from app.services.tender.analytics import TenderAnalyticsService
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
        raise HTTPException(status_code=500, detail="分析服務暫時無法使用")
