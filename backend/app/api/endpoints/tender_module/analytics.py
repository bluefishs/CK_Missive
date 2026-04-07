"""
標案分析 API — dashboard / battle-room / org-ecosystem / company-profile / price-analysis / price-trends
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas.common import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Endpoints
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
