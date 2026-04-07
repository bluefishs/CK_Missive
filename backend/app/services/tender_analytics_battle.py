"""
標案分析 — 投標戰情室 + 機關生態

拆分自 tender_analytics_service.py v5.5.1

Version: 1.0.0
"""
import logging
from typing import Optional, List, Dict, Any
from collections import Counter

from app.services.tender_search_service import TenderSearchService

logger = logging.getLogger(__name__)


async def battle_room(search: TenderSearchService, unit_id: str, job_number: str) -> dict:
    """投標戰情室 — 相似標案 + 競爭對手"""
    detail = await search.get_tender_detail(unit_id, job_number)
    if not detail:
        return {"error": "標案不存在"}

    title = detail.get("title", "")
    latest = detail.get("latest", {})
    agency = latest.get("agency_name", "")

    search_key = title[:10] if len(title) > 10 else title
    similar = await search.search_by_title(query=search_key, page=1)
    similar_records = [
        r for r in similar.get("records", [])[:10]
        if r.get("job_number") != job_number
    ]

    competitor_counter: Counter = Counter()
    competitor_wins: Counter = Counter()
    for r in similar_records:
        for w in r.get("winner_names", []):
            competitor_counter[w] += 1
            competitor_wins[w] += 1
        for b in r.get("bidder_names", []):
            competitor_counter[b] += 1

    competitors = []
    for name, total in competitor_counter.most_common(15):
        wins = competitor_wins.get(name, 0)
        competitors.append({
            "name": name,
            "appear_count": total,
            "win_count": wins,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
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


async def org_ecosystem(search: TenderSearchService, org_name: str, pages: int = 10) -> dict:
    """機關生態分析 — 歷年標案 + 得標廠商分布"""
    all_records: list = []
    for page in range(1, pages + 1):
        result = await search.search_by_org(org_name=org_name, page=page)
        records = result.get("records", [])
        if not records:
            break
        all_records.extend(records)

    if not all_records:
        return {"org_name": org_name, "total": 0}

    year_counter: Counter = Counter()
    vendor_counter: Counter = Counter()
    category_counter: Counter = Counter()
    for r in all_records:
        raw_date = r.get("raw_date") or r.get("date", "")
        year = str(raw_date)[:4] if raw_date else "未知"
        year_counter[year] += 1
        for w in r.get("winner_names", []):
            if w:
                vendor_counter[w] += 1
        category_counter[r.get("category", "未分類")] += 1

    return {
        "org_name": org_name,
        "total": len(all_records),
        "year_trend": [{"year": k, "count": v} for k, v in sorted(year_counter.items())[-15:]],
        "top_vendors": [{"name": k, "count": v} for k, v in vendor_counter.most_common(15)],
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
