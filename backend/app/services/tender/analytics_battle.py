"""
標案分析 — 投標戰情室 + 機關生態

拆分自 tender_analytics_service.py v5.5.1

Version: 2.0.0 — 去重 + 競爭強度 + 得標金額
"""
import re
import logging
from collections import Counter, defaultdict

from .search import TenderSearchService

logger = logging.getLogger(__name__)


def _parse_amount(raw) -> float:
    """安全解析金額"""
    if not raw:
        return 0
    try:
        return float(re.sub(r'[^\d.]', '', str(raw).replace(',', ''))) or 0
    except (ValueError, TypeError):
        return 0


async def battle_room(search: TenderSearchService, unit_id: str, job_number: str, detail=None) -> dict:
    """投標戰情室 — 去重相似標案 + 競爭對手含得標金額"""
    if not detail:
        detail = await search.get_tender_detail(unit_id, job_number)
    if not detail:
        return {"error": "標案不存在"}

    title = detail.get("title", "")
    latest = detail.get("latest", {})
    agency = latest.get("agency_name", "")

    # 搜尋相似標案 — 用標題前 10 字
    search_key = title[:10] if len(title) > 10 else title
    similar = await search.search_by_title(query=search_key, page=1)

    # 去重: 同 job_number 只保留最新一筆
    seen_jobs = {job_number}  # 排除自己
    similar_records = []
    for r in similar.get("records", []):
        jn = r.get("job_number", "")
        if jn and jn not in seen_jobs:
            seen_jobs.add(jn)
            similar_records.append(r)

    # 只保留前 8 筆用於統計 (與顯示一致)
    similar_records = similar_records[:8]

    # 競爭對手統計 — 每筆標案每家廠商只計一次
    competitor_data = defaultdict(lambda: {"appear": 0, "wins": 0, "total_amount": 0})
    for r in similar_records:
        budget = _parse_amount(r.get("budget") or latest.get("budget"))
        winners = set(w for w in r.get("winner_names", []) if w)
        bidders = set(b for b in r.get("bidder_names", []) if b)
        all_companies = winners | bidders  # 聯集去重
        for name in all_companies:
            competitor_data[name]["appear"] += 1
            if name in winners:
                competitor_data[name]["wins"] += 1
                competitor_data[name]["total_amount"] += budget

    competitors = []
    for name, d in sorted(competitor_data.items(), key=lambda x: x[1]["wins"], reverse=True)[:15]:
        competitors.append({
            "name": name,
            "appear_count": d["appear"],
            "win_count": d["wins"],
            "win_rate": round(d["wins"] / d["appear"] * 100, 1) if d["appear"] > 0 else 0,
            "total_amount": d["total_amount"],
        })

    return {
        "tender": {
            "title": title, "unit_id": unit_id, "job_number": job_number,
            "agency": agency, "budget": latest.get("budget"),
            "method": latest.get("method"), "deadline": latest.get("deadline"),
            "status": latest.get("status"),
        },
        "similar_tenders": similar_records[:8],
        "similar_count": len(similar_records),
        "competitors": competitors,
        "competitor_count": len(competitors),
    }


async def _db_org_fallback(org_name: str) -> dict:
    """方案 A 韌性後備：live openfun 空/限流時，改回本地 tender_records 標案清單。

    DB 有機關/標題/類別/日期（68k 筆招標公告），但無廠商得標維度（award/bidders 全空，L77 死結）
    → 回相同 result 形狀（前端可渲染）但 top_vendors 空、awarded_count=0、degraded=True。
    """
    import json as _json  # noqa: F401 (與呼叫端一致，避免 name error)
    from sqlalchemy import text
    from app.db.database import async_session_maker

    pat = f"%{org_name}%"
    year_counter: Counter = Counter()
    category_counter: Counter = Counter()
    recent: list = []
    total = 0
    try:
        async with async_session_maker() as db:
            total = (await db.execute(
                text("SELECT count(*) FROM tender_records WHERE unit_name ILIKE :pat"),
                {"pat": pat},
            )).scalar() or 0
            rows = (await db.execute(
                text(
                    "SELECT title, unit_name, unit_id, job_number, category, tender_type, "
                    "to_char(announce_date,'YYYY-MM-DD') AS date "
                    "FROM tender_records WHERE unit_name ILIKE :pat "
                    "ORDER BY announce_date DESC NULLS LAST LIMIT 300"
                ),
                {"pat": pat},
            )).mappings().all()
        for r in rows:
            y = (r["date"] or "")[:4] or "未知"
            year_counter[y] += 1
            category_counter[r["category"] or "未分類"] += 1
        recent = [{
            "title": r["title"] or "", "date": r["date"] or "",
            "type": r["tender_type"] or "", "category": r["category"] or "",
            "unit_name": r["unit_name"] or "", "unit_id": r["unit_id"] or "",
            "job_number": r["job_number"] or "", "winner_names": [],
        } for r in rows[:20]]
    except Exception as e:
        logger.warning(f"org_ecosystem DB fallback failed org={org_name}: {e}")

    return {
        "org_name": org_name,
        "total": total,
        "awarded_count": 0,
        "year_trend": [{"year": k, "count": v} for k, v in sorted(year_counter.items())[-15:]],
        "top_vendors": [],
        "category_distribution": [{"name": k, "value": v} for k, v in category_counter.most_common(10)],
        "recent_tenders": recent,
        "degraded": True,
        "degraded_reason": "外部得標資料源暫時限流，以下為本地標案清單（暫無廠商/得標分析），稍後自動重試。",
    }


async def org_ecosystem(search: TenderSearchService, org_name: str, pages: int = 10) -> dict:
    """機關生態分析 — 年度 Top 10 廠商 + 競爭強度 + 得標金額 (Redis 快取 30min)"""
    import asyncio
    import json as _json

    # Redis 結果快取 (30 min)
    redis = None
    cache_key = f"tender:org_ecosystem:{org_name}"
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            cached = await redis.get(cache_key)
            if cached:
                return _json.loads(cached)
    except Exception:
        pass

    # 並行搜尋: orgname + title (機關改名也能找到舊標案)
    async def fetch_org(p):
        return await search.search_by_org(org_name=org_name, page=p)
    async def fetch_title(p):
        return await search.search_by_title(query=org_name, page=p)

    tasks = [fetch_org(p) for p in range(1, min(pages, 5) + 1)]
    # 用機關名稱的核心部分搜標題 (處理改名問題)
    short_name = org_name
    for suffix in ['分局', '管理處', '工程處', '服務中心', '中心', '局']:
        idx = org_name.rfind(suffix)
        if idx > 4:
            short_name = org_name[max(0, idx - 6):idx + len(suffix)]
            break
    tasks += [fetch_title(p) for p in range(1, 3)]
    if short_name != org_name:
        async def fetch_short(p):
            return await search.search_by_title(query=short_name, page=p)
        tasks += [fetch_short(p) for p in range(1, 3)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    seen_jobs = set()
    all_records = []
    for item in results:
        if isinstance(item, Exception):
            continue
        for r in item.get("records", []):
            jn = r.get("job_number", "")
            if jn and jn not in seen_jobs:
                seen_jobs.add(jn)
                all_records.append(r)

    if not all_records:
        # 方案 A（2026-07-04 owner 授權）韌性強化：live openfun 空/限流 → 回本地 DB 標案清單
        #   （degraded），而非整頁 total:0。成功路徑不變；degraded 結果快取較短(5min)以便盡快重試 live。
        fallback = await _db_org_fallback(org_name)
        if redis:
            try:
                await redis.set(cache_key, _json.dumps(fallback, ensure_ascii=False, default=str), ex=300)
            except Exception:
                pass
        return fallback

    # 基本統計
    year_counter: Counter = Counter()
    category_counter: Counter = Counter()

    # 廠商詳細統計 — 出現次數 + 得標次數 + 得標金額
    vendor_appear: Counter = Counter()
    vendor_wins: Counter = Counter()
    vendor_amount: Counter = Counter()

    for r in all_records:
        raw_date = r.get("raw_date") or r.get("date", "")
        year = str(raw_date)[:4] if raw_date else "未知"
        year_counter[year] += 1
        category_counter[r.get("category", "未分類")] += 1

        # 所有參與廠商 (投標+得標)
        all_companies = set(r.get("winner_names", []) + r.get("bidder_names", []))
        for c in all_companies:
            if c:
                vendor_appear[c] += 1

        # 得標廠商
        for w in r.get("winner_names", []):
            if w:
                vendor_wins[w] += 1

    # Top 10 廠商排行 — 含競爭強度
    top_vendors = []
    for name, appear in vendor_appear.most_common(15):
        wins = vendor_wins.get(name, 0)
        top_vendors.append({
            "name": name,
            "appear_count": appear,
            "win_count": wins,
            "win_rate": round(wins / appear * 100, 1) if appear > 0 else 0,
        })

    # 預算→決標折率統計 (用於推估未決標案件)
    budget_award_pairs = []
    for r in all_records:
        # 從 winner_names 有值的記錄推算有決標
        if r.get("winner_names"):
            budget_award_pairs.append(r)

    result = {
        "org_name": org_name,
        "total": len(all_records),
        "awarded_count": len(budget_award_pairs),
        "year_trend": [{"year": k, "count": v} for k, v in sorted(year_counter.items())[-15:]],
        "top_vendors": top_vendors,
        "category_distribution": [{"name": k, "value": v} for k, v in category_counter.most_common(10)],
        "recent_tenders": [
            {
                "title": r.get("title", ""), "date": r.get("date", ""),
                "type": r.get("type", ""), "category": r.get("category", ""),
                "unit_name": r.get("unit_name", ""), "unit_id": r.get("unit_id", ""),
                "job_number": r.get("job_number", ""),
                "winner_names": r.get("winner_names", []),
            }
            for r in all_records[:20]
        ],
    }

    # 寫入 Redis 快取 (30 min)
    if redis:
        try:
            await redis.set(cache_key, _json.dumps(result, ensure_ascii=False, default=str), ex=1800)
        except Exception:
            pass

    return result
