"""
Tender Data Transformer -- record normalisation, detail parsing, graph building.

Extracted from tender_search_service.py to keep the search service under 500L.

Version: 1.0.0
Created: 2026-04-08
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def normalize_record(record: dict) -> dict:
    """Standardise a list-level tender record."""
    brief = record.get("brief", {})
    companies = brief.get("companies", {})

    # Parse date
    raw_date = record.get("date", 0)
    date_str = ""
    if raw_date:
        try:
            d = datetime.strptime(str(raw_date), "%Y%m%d")
            date_str = d.strftime("%Y-%m-%d")
        except ValueError:
            date_str = str(raw_date)

    # Identify winners vs bidders
    name_key = companies.get("name_key", {})
    winner_names: List[str] = []
    bidder_names: List[str] = []
    for name, keys in name_key.items():
        is_winner = any(
            "得標廠商" in k and "未得標" not in k
            for k in keys
        )
        if is_winner:
            winner_names.append(name)
        else:
            bidder_names.append(name)

    return {
        "date": date_str,
        "raw_date": raw_date,
        "title": brief.get("title", ""),
        "type": brief.get("type", ""),
        "category": clean_category(brief.get("category", "")),
        "unit_id": record.get("unit_id", ""),
        "unit_name": record.get("unit_name", ""),
        "job_number": record.get("job_number", ""),
        "company_names": companies.get("names", []),
        "company_ids": companies.get("ids", []),
        "winner_names": winner_names,
        "bidder_names": bidder_names,
        "tender_api_url": record.get("tender_api_url", ""),
        "matched_keyword": record.get("matched_keyword"),
    }


def normalize_detail(data: dict) -> dict:
    """Standardise a tender detail response (multiple events/records)."""
    unit_name = data.get("unit_name", "")
    records = data.get("records", [])
    if not records:
        return {"unit_name": unit_name, "events": []}

    events = []
    for rec in records:
        detail = rec.get("detail", {})
        events.append({
            "date": rec.get("date"),
            "type": rec.get("brief", {}).get("type", ""),
            "title": rec.get("brief", {}).get("title", ""),
            "category": rec.get("brief", {}).get("category", ""),
            "job_number": rec.get("job_number", ""),
            "detail": {
                "agency_name": detail.get("機關資料:機關名稱", ""),
                "agency_unit": detail.get("機關資料:單位名稱", ""),
                "agency_address": detail.get("機關資料:機關地址", ""),
                "contact_person": detail.get("機關資料:聯絡人", ""),
                "contact_phone": detail.get("機關資料:聯絡電話", ""),
                "contact_email": detail.get("機關資料:電子郵件信箱", ""),
                "budget": detail.get("採購資料:預算金額", ""),
                "procurement_type": detail.get("採購資料:標的分類", ""),
                "method": detail.get("招標資料:招標方式", ""),
                "award_method": detail.get("招標資料:決標方式", ""),
                "announce_date": detail.get("招標資料:公告日", ""),
                "deadline": detail.get("招標資料:截止投標", detail.get("領投開標:截止投標", "")),
                "open_date": detail.get("領投開標:開標日期", ""),
                "status": detail.get("招標資料:招標狀態", ""),
                "pcc_url": detail.get("url", ""),
            },
            "award_details": extract_award_details(detail),
            "companies": rec.get("brief", {}).get("companies", {}).get("names", []),
        })

    # Back-fill unit_name from event detail
    if not unit_name and events:
        unit_name = events[0].get("detail", {}).get("agency_name", "") or ""

    # Merge all event details -- different announcement types carry different fields
    merged_detail: Dict[str, Any] = {}
    for evt in events:
        for k, v in evt.get("detail", {}).items():
            if v and not merged_detail.get(k):
                merged_detail[k] = v

    return {
        "unit_name": unit_name,
        "job_number": records[0].get("job_number", ""),
        "title": records[0].get("brief", {}).get("title", ""),
        "events": events,
        "latest": events[0] if events else None,
        "merged_detail": merged_detail,
    }


def extract_award_details(detail: dict) -> dict:
    """Extract price/award information from PCC API detail data.

    PCC API uses Chinese key names, e.g.:
      - 決標資料:決標金額, 決標資料:決標日期
      - 採購資料:底價
      - 決標品項:第N品項:得標廠商, 決標品項:第N品項:決標金額
    """
    try:
        award_date = detail.get("決標資料:決標日期") or None
        total_award_amount = parse_amount(detail.get("決標資料:決標金額"))
        floor_price = parse_amount(detail.get("採購資料:底價"))

        award_items = []
        for i in range(1, 21):  # scan up to 20 items
            item_prefix = f"決標品項:第{i}品項"
            winner_key = f"{item_prefix}:得標廠商"
            amount_key = f"{item_prefix}:決標金額"

            winner_name = detail.get(winner_key)
            if winner_name is None:
                alt_key = f"{item_prefix}:得標廠商1:得標廠商"
                winner_name = detail.get(alt_key)

            if winner_name is None and detail.get(amount_key) is None:
                break

            award_items.append({
                "item_no": i,
                "winner": winner_name,
                "amount": parse_amount(detail.get(amount_key)),
            })

        return {
            "award_date": award_date,
            "total_award_amount": total_award_amount,
            "floor_price": floor_price,
            "award_items": award_items,
        }
    except Exception as e:
        logger.warning(f"Failed to extract award details: {e}")
        return {
            "award_date": None,
            "total_award_amount": None,
            "floor_price": None,
            "award_items": [],
        }


def parse_amount(raw: Any) -> Optional[float]:
    """Safely parse an amount string to float, supporting comma-separated thousands."""
    if raw is None:
        return None
    try:
        cleaned = re.sub(r'[^\d.]', '', str(raw).replace(',', ''))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def clean_category(raw: str) -> str:
    """Clean category: '482-勞務類' -> '勞務類', '2-工程類' -> '工程類'."""
    if not raw:
        return "未分類"
    cleaned = re.sub(r'^[\d.]+-', '', raw).strip()
    cleaned = re.sub(r'\([\d.]+\)', '', cleaned).strip()
    return cleaned or raw


def match_category(record: dict, category: str) -> bool:
    """Check if a tender record matches the given category."""
    cat = record.get("brief", {}).get("category", "")
    return category in cat


def build_tender_graph(
    records: List[dict], query: str,
) -> Dict[str, Any]:
    """
    Build a tender knowledge graph -- Agency -> Tender -> Company network.

    Args:
        records: Already-normalised tender records.
        query: Original search query.

    Returns:
        {nodes: [...], edges: [...], stats: {...}}
    """
    nodes: Dict[str, dict] = {}
    edges: list = []

    for r in records:
        # Tender node
        tender_id = f"tender:{r['job_number']}"
        nodes[tender_id] = {
            "id": tender_id, "name": r["title"][:40],
            "type": "tender", "category": r.get("category", ""),
            "date": r.get("date", ""),
        }

        # Agency node
        if r.get("unit_name"):
            unit_id = f"agency:{r['unit_id']}"
            if unit_id not in nodes:
                nodes[unit_id] = {
                    "id": unit_id, "name": r["unit_name"],
                    "type": "agency",
                }
            edges.append({
                "source": unit_id, "target": tender_id,
                "relation": "招標",
            })

        # Company nodes
        for i, company in enumerate(r.get("company_names", [])):
            comp_id = (
                f"company:{r.get('company_ids', [''])[i]}"
                if i < len(r.get("company_ids", []))
                else f"company:{company}"
            )
            if comp_id not in nodes:
                nodes[comp_id] = {
                    "id": comp_id, "name": company,
                    "type": "company",
                }
            edges.append({
                "source": tender_id, "target": comp_id,
                "relation": "得標",
            })

    return {
        "query": query,
        "nodes": list(nodes.values()),
        "edges": edges,
        "stats": {
            "tenders": len([n for n in nodes.values() if n["type"] == "tender"]),
            "agencies": len([n for n in nodes.values() if n["type"] == "agency"]),
            "companies": len([n for n in nodes.values() if n["type"] == "company"]),
            "edges": len(edges),
        },
    }
