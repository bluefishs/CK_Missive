"""
標案分析 — 底價分析 + 廠商分析

拆分自 tender_analytics_service.py v5.5.1

Version: 1.0.0
"""
import re
import logging
from typing import Optional, List, Dict, Any
from collections import Counter

from app.services.tender_search_service import TenderSearchService

logger = logging.getLogger(__name__)


def _safe_parse_amount(raw) -> float | None:
    """安全解析金額字串"""
    if raw is None:
        return None
    try:
        cleaned = re.sub(r'[^\d.]', '', str(raw).replace(',', ''))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


async def price_analysis(search: TenderSearchService, unit_id: str, job_number: str, detail=None) -> dict:
    """底價分析 — 單一標案的預算/底價/決標金額"""
    if not detail:
        detail = await search.get_tender_detail(unit_id, job_number)
    if not detail:
        return {"error": "標案不存在"}

    title = detail.get("title", "")
    events = detail.get("events", [])

    budget = None
    floor_price = None
    award_amount = None
    award_date = None
    award_items = []

    for evt in events:
        det = evt.get("detail", {})
        if not budget:
            budget = _safe_parse_amount(det.get("budget"))
        award_det = evt.get("award_details")
        if award_det:
            if not floor_price:
                floor_price = award_det.get("floor_price")
            if not award_amount:
                award_amount = award_det.get("total_award_amount")
            if not award_date:
                award_date = award_det.get("award_date")
            award_items = award_det.get("award_items", [])

    analysis = {}
    if budget and award_amount:
        analysis["budget_award_variance_pct"] = round((budget - award_amount) / budget * 100, 1)
    if floor_price and award_amount:
        analysis["floor_award_variance_pct"] = round((floor_price - award_amount) / floor_price * 100, 1)
    if budget and floor_price:
        analysis["budget_floor_variance_pct"] = round((budget - floor_price) / budget * 100, 1)
    if budget and award_amount:
        analysis["savings_rate_pct"] = round((budget - award_amount) / budget * 100, 1)

    return {
        "tender": {"title": title, "unit_id": unit_id, "job_number": job_number, "unit_name": detail.get("unit_name", "")},
        "prices": {"budget": budget, "floor_price": floor_price, "award_amount": award_amount, "award_date": award_date},
        "analysis": analysis,
        "award_items": award_items,
    }


async def price_trends(search: TenderSearchService, query: str, pages: int = 3) -> dict:
    """價格趨勢 — 多筆標案的預算/底價/決標統計"""
    import statistics as stats_mod

    all_records = []
    for page in range(1, pages + 1):
        result = await search.search_by_title(query=query, page=page)
        records = result.get("records", [])
        if not records:
            break
        all_records.extend(records)

    budgets, floors, awards = [], [], []
    entries = []

    for r in all_records[:50]:
        detail = await search.get_tender_detail(r.get("unit_id", ""), r.get("job_number", ""))
        if not detail:
            continue
        for evt in detail.get("events", []):
            det = evt.get("detail", {})
            b = _safe_parse_amount(det.get("budget"))
            ad = evt.get("award_details") or {}
            f = ad.get("floor_price")
            a = ad.get("total_award_amount")
            if b: budgets.append(b)
            if f: floors.append(f)
            if a: awards.append(a)
            entries.append({
                "title": r.get("title", "")[:60], "date": r.get("date", ""),
                "unit_name": r.get("unit_name", ""),
                "budget": b, "floor_price": f, "award_amount": a,
            })
            break

    def _agg(values: list) -> dict:
        if not values:
            return {"count": 0, "min": None, "max": None, "avg": None, "median": None}
        return {
            "count": len(values), "min": min(values), "max": max(values),
            "avg": round(sum(values) / len(values), 0),
            "median": round(stats_mod.median(values), 0),
        }

    award_rate = round(len(awards) / len(all_records) * 100, 1) if all_records else None

    ranges = Counter()
    for b in budgets:
        if b < 1_000_000: ranges["100萬以下"] += 1
        elif b < 5_000_000: ranges["100~500萬"] += 1
        elif b < 10_000_000: ranges["500~1000萬"] += 1
        elif b < 50_000_000: ranges["1000~5000萬"] += 1
        else: ranges["5000萬以上"] += 1

    return {
        "query": query, "total": len(all_records), "samples": len(entries),
        "stats": {"budget": _agg(budgets), "floor_price": _agg(floors), "award_amount": _agg(awards), "award_rate_pct": award_rate},
        "distribution": [{"range": k, "count": v} for k, v in ranges.most_common()],
        "entries": entries[:20],
    }


async def company_profile(search: TenderSearchService, company_name: str, pages: int = 3) -> dict:
    """廠商得標分析 — 歷年得標 + 機關分布 + 類別分布"""
    all_records: list = []
    for page in range(1, pages + 1):
        result = await search.search_by_company(company_name=company_name, page=page)
        records = result.get("records", [])
        if not records:
            break
        all_records.extend(records)

    if not all_records:
        return {"company_name": company_name, "total": 0}

    year_counter: Counter = Counter()
    agency_counter: Counter = Counter()
    category_counter: Counter = Counter()
    won_count = 0

    for r in all_records:
        raw_date = r.get("raw_date") or r.get("date", "")
        year = str(raw_date)[:4] if raw_date else "未知"
        year_counter[year] += 1
        agency_counter[r.get("unit_name", "未知")] += 1
        category_counter[r.get("category", "未分類")] += 1
        winners = r.get("winner_names") or []
        if any(company_name in w or w in company_name for w in winners):
            won_count += 1
            r["_is_won"] = True

    recent = [{
        "title": r.get("title", ""), "date": r.get("date", ""),
        "unit_name": r.get("unit_name", ""), "unit_id": r.get("unit_id", ""),
        "job_number": r.get("job_number", ""), "type": r.get("type", ""),
        "category": r.get("category", ""),
        "winner_names": r.get("winner_names", []), "bidder_names": r.get("bidder_names", []),
        "is_won": r.get("_is_won", False),
    } for r in all_records[:20]]

    return {
        "company_name": company_name, "total": len(all_records),
        "won_count": won_count,
        "win_rate": round(won_count / len(all_records) * 100, 1) if all_records else 0,
        "year_trend": [{"year": k, "count": v} for k, v in sorted(year_counter.items())],
        "top_agencies": [{"name": k, "count": v} for k, v in agency_counter.most_common(15)],
        "category_distribution": [{"name": k, "value": v} for k, v in category_counter.most_common(10)],
        "recent_tenders": recent,
    }
