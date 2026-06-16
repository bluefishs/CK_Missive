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
    # 統一口徑（owner 定案）：今日標案＝唯一「日」單元；其餘卡片皆「週(近7日)」去重統計，
    #   並以 DB 同源（fetch/count_complete_tenders）覆寫 stats/清單/日期範圍，根治：
    #   ①兩頁口徑不一 ②本週嚴重低估(爬蟲只今日) ③決標清單「停留 3 月」陳舊
    #   ④日期範圍標籤錯亂(如最新決標 03-19) ⑤公開徵求區間。決標/得標廠商分卡語意保留。
    from datetime import date as _date, timedelta as _td
    try:
        stats = result.setdefault("stats", {})
        dr = result.setdefault("date_ranges", {})
        _today = _date.today()
        _wk_start = _today - _td(days=6)
        today_lbl = _today.strftime("%m-%d")
        week_lbl = f"{_wk_start.strftime('%m-%d')}~{_today.strftime('%m-%d')}"

        # 今日標案（唯一「日」單元；含報價單去重，與 /tender/search 同源）
        stats["latest_bid"] = await count_complete_tenders(db, days_back=0)
        result["latest_bid_list"] = await fetch_complete_tenders(db, days_back=0, limit=500)
        dr["latest_bid"] = today_lbl

        # ── 以下皆「週(近7日)」去重 ──
        stats["week_new_bid"] = await count_complete_tenders(db, days_back=6)          # 本週標案
        result["week_new_bid_list"] = await fetch_complete_tenders(db, days_back=6, limit=500)
        dr["week_bid"] = week_lbl

        stats["week_new_award"] = await count_complete_tenders(db, days_back=6, kind="award")  # 本週決標
        result["week_new_award_list"] = await fetch_complete_tenders(db, days_back=6, limit=500, kind="award", order="date")
        dr["week_award"] = week_lbl

        stats["failed_award"] = await count_complete_tenders(db, days_back=6, kind="failed")    # 無法決標(週)
        result["failed_award_list"] = await fetch_complete_tenders(db, days_back=6, limit=500, kind="failed", order="date")
        dr["failed"] = week_lbl

        stats["rfp_count"] = await count_complete_tenders(db, days_back=6, kind="rfp")          # 公開徵求(週)
        result["rfp_list"] = await fetch_complete_tenders(db, days_back=6, limit=500, kind="rfp")
        dr["rfp"] = week_lbl

        result["today_total_count"] = stats["latest_bid"]
        result["week_total_count"] = stats["week_new_bid"]
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
