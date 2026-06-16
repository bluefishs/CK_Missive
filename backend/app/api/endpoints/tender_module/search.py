"""
標案搜尋 API — search / detail / detail-full / search-company / recommend / realtime
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tender.search import TenderSearchService
from app.schemas.common import SuccessResponse
from app.schemas.tender_admin import (
    TenderCompanySearchRequest,
    TenderDetailRequest,
    TenderRecommendRequest,
    TenderSearchRequest,
)
from app.db.database import get_async_db as get_db

logger = logging.getLogger(__name__)

router = APIRouter()


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
    """搜尋標案 — DB 優先 + g0v + ezbid 三軌合併"""
    from datetime import datetime, timedelta

    # Step 0: DB 快速查詢 (毫秒級)
    db_records = []
    try:
        from app.db.database import AsyncSessionLocal
        from app.services.tender.cache import search_from_db
        async with AsyncSessionLocal() as cache_db:
            db_records = await search_from_db(cache_db, req.query, limit=20)
    except Exception:
        pass

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
            from app.services.tender.ezbid_scraper import EzbidScraper
            from app.core.redis_client import get_redis
            try:
                _redis = await get_redis()
            except Exception:
                _redis = None
            scraper = EzbidScraper(redis_client=_redis)
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

    # 合併 DB 結果 (補充 API 未覆蓋的歷史資料)
    if db_records:
        seen_titles = {r.get("title", "")[:20] for r in result.get("records", [])}
        for r in db_records:
            if r.get("title", "")[:20] not in seen_titles:
                seen_titles.add(r.get("title", "")[:20])
                r["source"] = "db"
                result["records"].append(r)
        result["total_records"] = len(result["records"])

    # Relevance re-ranking — 合併後按標題相似度重排序
    if result.get("records") and len(req.query) > 5:
        from app.services.tender.search_query import rerank_by_title_similarity
        result["records"] = rerank_by_title_similarity(
            result["records"], req.query, top_k=30,
        )
        result["total_records"] = len(result["records"])

    # 搜尋結果自動入庫 — 2026-04-24 改非同步背景任務，不阻塞 response
    try:
        import asyncio as _aio
        from app.db.database import AsyncSessionLocal
        from app.services.tender.cache import save_search_results

        async def _bg_save(records_snapshot):
            try:
                async with AsyncSessionLocal() as cache_db:
                    await save_search_results(cache_db, records_snapshot, source="pcc")
            except Exception as e:
                import logging as _logging
                _logging.getLogger(__name__).debug(f"bg tender save failed: {e}")

        _aio.create_task(_bg_save(list(result.get("records", []))[:50]))
    except Exception:
        pass

    # L51 task F: page view counter
    try:
        from app.services.tender.metrics import get_tender_metrics
        get_tender_metrics().page_view.labels(page="search").inc()
    except Exception:
        pass

    return SuccessResponse(data=result)


@router.post("/detail")
async def get_tender_detail(
    req: TenderDetailRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """取得標案詳情 (含歷次公告)

    支援兩種 ID：
    - PCC: unit_id + job_number (e.g. "A.19.4.8" + "115-1528-02")
    - ezbid: unit_id = 純數字 ezbid_id, job_number = None
    """
    # ezbid-only: 純數字 + 無 job_number → 查 DB tender_records
    is_ezbid = req.unit_id.isdigit() and not req.job_number
    if is_ezbid:
        # L51 task F: page view counter (ezbid path)
        try:
            from app.services.tender.metrics import get_tender_metrics
            get_tender_metrics().page_view.labels(page="detail").inc()
        except Exception:
            pass
        # 2026-04-24 修復：原 SQL 引用不存在的 ezbid_url 欄位導致 silent fail（ADR-0028）
        import logging as _log
        _logger = _log.getLogger(__name__)
        try:
            from app.db.database import async_session_maker
            from sqlalchemy import text as sa_text
            async with async_session_maker() as db:
                r = await db.execute(sa_text("""
                    SELECT title, unit_name, budget, announce_date, status,
                           unit_id, job_number, source, raw_data,
                           pcc_match_unit_id, pcc_match_job_number,
                           pcc_match_confidence, pcc_match_at
                    FROM tender_records
                    WHERE ezbid_id = :eid
                    ORDER BY announce_date DESC LIMIT 1
                """), {"eid": req.unit_id})
                row = r.one_or_none()
                if row:
                    # 從 raw_data 取 ezbid_url；若無則組預設 URL
                    ezbid_url = f"https://cf.ezbid.tw/tender/{req.unit_id}"
                    if row[8]:
                        try:
                            import json as _json
                            raw = _json.loads(row[8])
                            ezbid_url = raw.get("ezbid_url") or ezbid_url
                        except Exception:
                            pass

                    result = {
                        "kind": "ezbid",  # ADR-0032 discriminated union
                        "ezbid_id": req.unit_id,
                        "unit_id": row[5] or req.unit_id,
                        "job_number": row[6] or "",
                        "title": row[0] or "",
                        "unit_name": row[1] or "",
                        "budget": row[2],
                        "announce_date": str(row[3]) if row[3] else "",
                        "status": row[4] or "",
                        "source": "ezbid_db",
                        "ezbid_url": ezbid_url,
                    }
                    # L51 (2026-05-28) ADR-0046 Phase 3 對應 PCC link 暴露給前端
                    # 233/27286 (0.85%) HIGH-matched ezbid 才有，UI 渲染「對應 PCC」區塊 + 跳轉
                    if row[9] and row[10]:
                        result["pcc_match"] = {
                            "unit_id": row[9],
                            "job_number": row[10],
                            "confidence": float(row[11]) if row[11] is not None else None,
                            "matched_at": str(row[12]) if row[12] else None,
                        }
                    # 如果有 PCC unit_id + job_number，嘗試補充 PCC 詳情
                    if row[5] and row[6] and not row[5].isdigit():
                        pcc_result = await service.get_tender_detail(row[5], row[6])
                        if pcc_result:
                            pcc_result["kind"] = "pcc"
                            pcc_result["ezbid_url"] = result["ezbid_url"]
                            return SuccessResponse(data=pcc_result)
                    return SuccessResponse(data=result)
                # row is None → 真的查無
                _logger.info(f"ezbid detail not found: ezbid_id={req.unit_id}")
        except Exception as e:
            _logger.error(f"ezbid detail query failed for {req.unit_id}: {e}", exc_info=True)
        return SuccessResponse(data=None, message="查無此 ezbid 標案")

    result = await service.get_tender_detail(
        unit_id=req.unit_id, job_number=req.job_number or "",
    )
    if not result:
        return SuccessResponse(data=None, message="查無此標案")
    # ADR-0032: PCC response 明確標記 kind
    result["kind"] = "pcc"
    # L51 task F: page view counter
    try:
        from app.services.tender.metrics import get_tender_metrics
        get_tender_metrics().page_view.labels(page="detail").inc()
    except Exception:
        pass
    return SuccessResponse(data=result)


@router.post("/detail-full")
async def get_tender_detail_full(
    req: TenderDetailRequest,
    service: TenderSearchService = Depends(get_tender_service),
):
    """標案完整戰情 — 詳情 + 相似標案 + 機關生態 + 競爭對手 (並行, Redis 快取)"""
    import asyncio
    import json as _json
    from app.services.tender.analytics import TenderAnalyticsService

    # Redis 快取 (整個 detail-full 結果, 2hr)
    try:
        from app.core.redis_client import get_redis
        _redis = await get_redis()
        if _redis:
            cache_key = f"tender:detail-full:{req.unit_id}:{req.job_number}"
            cached = await _redis.get(cache_key)
            if cached:
                return SuccessResponse(data=_json.loads(cached))
    except Exception:
        _redis = None

    analytics = TenderAnalyticsService()

    # Step 1: 取得詳情 (需先知道機關名稱)
    detail = await service.get_tender_detail(req.unit_id, req.job_number)
    if not detail:
        return SuccessResponse(data=None, message="查無此標案")

    agency_name = detail.get("unit_name", "")

    # Step 2: 並行取得戰情+底價+機關生態 (傳入 detail 避免重複查詢)
    from app.services.tender.analytics_battle import battle_room as _battle_room
    battle_task = _battle_room(service, req.unit_id, req.job_number, detail=detail)
    from app.services.tender.analytics_price import price_analysis as _price_analysis
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

    result_data = {
        "detail": detail,
        "battle_room": battle,
        "org_ecosystem": org_eco,
        "price_analysis": price if not price.get("error") else None,
        "price_estimate": estimate,
    }

    # 存入 Redis 快取 (2hr)
    try:
        if _redis:
            await _redis.setex(cache_key, 7200, _json.dumps(result_data, default=str, ensure_ascii=False))
    except Exception:
        pass

    return SuccessResponse(data=result_data)


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
    """智能推薦 v2 (L51.5 統一版, 2026-05-29)

    Owner 反饋：/tender/search 推薦 14 筆與 LINE 推薦 3 筆無關聯，管理混淆。

    修法：兩端統一使用 business_recommendation.find_business_recommendations
          (3 條基本面 AND + 3 重業務信號 OR + 加權排序)

    保留原 response 結構 (keywords/total/today_records/records) 不破壞 frontend，
    新增 match_signals 標籤透明化推薦原因。
    """
    from app.extended.models.tender import TenderSubscription
    from app.services.tender.business_recommendation import find_business_recommendations

    # 取訂閱關鍵字（給 frontend 顯示「依訂閱關鍵字推薦」label）
    subs = await db.execute(
        select(TenderSubscription).where(TenderSubscription.is_active == True)  # noqa: E712
    )
    keywords = [s.keyword for s in subs.scalars().all()]

    # L51.5 統一邏輯：用 LINE 業務推薦同一個 SQL
    # days_back=7 (與 LINE 1 日不同 — UI 場景看更多)
    # budget_min=1_000_000 (與 LINE 同)
    # limit=50 (UI 場景上限，LINE 是 20)
    recs = await find_business_recommendations(
        db, days_back=7, budget_min=1_000_000, limit=50,
    )

    def adapt(r):
        """v2 結果 → frontend TenderRecord shape + 透明化標籤"""
        return {
            "date": r.get("announce_date", ""),
            "raw_date": int(
                str(r.get("announce_date", "0")).replace("-", "")
            ) if r.get("announce_date") else 0,
            "title": r.get("title", ""),
            "type": "",  # v2 SQL 暫無此欄
            "category": "",
            "unit_id": r.get("unit_id", ""),
            "unit_name": r.get("unit_name", ""),
            "job_number": r.get("job_number", "") or "",
            "company_names": [], "company_ids": [],
            "winner_names": [], "bidder_names": [],
            "tender_api_url": "",
            "source": r.get("source", ""),
            "budget": r.get("budget", 0),
            # L51.5 frontend 既有欄位 (gold tag)
            "matched_keyword": (
                r["matched_keywords"][0] if r.get("matched_keywords") else None
            ),
            # L51.5 透明化標籤（前端可用於 tooltip / detail view）
            "match_signals": {
                "matched_keywords": r.get("matched_keywords", []),
                "is_contracted": r.get("is_contracted", False),
                "is_cooperated": r.get("is_cooperated", False),
                "agency_match_count": r.get("agency_match_count", 0),
                "match_score": (
                    (3 if r.get("matched_keywords") else 0)
                    + (2 if r.get("is_contracted") else 0)
                    + (1 if r.get("is_cooperated") else 0)
                ),
            },
        }

    # 業務推薦 = Option B 相關性推薦（關鍵字＝工項含同義詞 / 精準局處工程）；可為 0＝本期無相關（誠實）
    business_records = [adapt(r) for r in recs]

    # 今日最新 = 今日「全部」新案（活動量）。L75 卡片語意（owner 定案 Option A，2026-06-16）：
    #   「今日最新」反映系統活動，不套相關性/預算過濾（否則 PCC budget 多 NULL + Option B 過濾
    #    → 卡片恆 0 看似系統壞）。「業務推薦」維持相關性過濾。兩卡語意分離。
    today_rows = await db.execute(text("""
        SELECT COALESCE(pcc_match_unit_id, unit_id) AS unit_id,
               COALESCE(pcc_match_job_number, job_number) AS job_number,
               title, unit_name, budget, announce_date, source, category
        FROM tender_records
        WHERE announce_date = CURRENT_DATE
        ORDER BY (budget IS NOT NULL) DESC, budget DESC NULLS LAST, id DESC
        LIMIT 1000
    """))

    def adapt_today(row):
        """今日新案 row → frontend TenderRecord shape（活動量，無推薦標籤）。"""
        return {
            "date": str(row.announce_date) if row.announce_date else "",
            "raw_date": int(str(row.announce_date).replace("-", "")) if row.announce_date else 0,
            "title": row.title or "",
            "type": "", "category": row.category or "",
            "unit_id": row.unit_id or "", "unit_name": row.unit_name or "",
            "job_number": row.job_number or "",
            "company_names": [], "company_ids": [], "winner_names": [], "bidder_names": [],
            "tender_api_url": "", "source": row.source or "", "budget": row.budget or 0,
            "matched_keyword": None,
            "match_signals": {
                "matched_keywords": [], "is_contracted": False,
                "is_cooperated": False, "agency_match_count": 0, "match_score": 0,
            },
        }

    today_records = [adapt_today(row) for row in today_rows]

    return SuccessResponse(data={
        "keywords": keywords,
        "total": len(business_records),
        "today_records": today_records,   # 今日最新（活動量）
        "records": business_records,      # 業務推薦（Option B 相關性）
    })


@router.post("/realtime")
async def realtime_tenders(req: TenderSearchRequest):
    """即時標案 — 爬取 ezbid.tw 最新資料 (補充 PCC API 延遲)"""
    from app.services.tender.ezbid_scraper import EzbidScraper

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
