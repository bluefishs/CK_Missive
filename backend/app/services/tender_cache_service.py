"""
標案快取服務 — 搜尋結果持久化到 DB

自動將 g0v/ezbid 搜尋結果寫入 tender_records，
後續查詢優先從 DB 取得，減少外部 API 呼叫。

Version: 1.0.0
"""
import re
import json
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.core.name_utils import normalize_for_match

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> Optional[date]:
    """解析日期字串 (YYYY-MM-DD)"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_amount(raw) -> Optional[float]:
    """解析金額"""
    if not raw:
        return None
    try:
        cleaned = re.sub(r'[^\d.]', '', str(raw).replace(',', ''))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


async def _ingest_tender_entities(db: AsyncSession, records: List[Dict[str, Any]]) -> int:
    """將標案中的機關與廠商名稱寫入 CanonicalEntity (知識圖譜自動入圖)

    Uses INSERT...ON CONFLICT to upsert: new entities are created,
    existing ones get mention_count incremented.
    """
    names: set[str] = set()

    # Collect unique unit_name (org) from tender records
    for r in records:
        unit_name = (r.get("unit_name") or "").strip()
        if unit_name:
            names.add(unit_name)

    # Collect unique company names from winner/bidder lists
    for r in records:
        for key in ("winner_names", "bidder_names"):
            for name in (r.get(key) or []):
                if name and name.strip():
                    names.add(name.strip())

    if not names:
        return 0

    ingested = 0
    for raw_name in names:
        normalized = normalize_for_match(raw_name)
        if not normalized:
            continue
        try:
            await db.execute(text("""
                INSERT INTO canonical_entities (canonical_name, entity_type, description, mention_count)
                VALUES (:name, 'org', :desc, 1)
                ON CONFLICT (canonical_name, entity_type) DO UPDATE
                    SET mention_count = canonical_entities.mention_count + 1,
                        last_seen_at = NOW()
            """), {"name": normalized, "desc": f"Auto-ingested from tender: {raw_name}"})
            ingested += 1
        except Exception as e:
            logger.debug(f"Ingest tender entity '{raw_name}' failed: {e}")
            continue

    if ingested > 0:
        logger.info(f"Ingested {ingested} tender entities into KG")
    return ingested


async def save_search_results(db: AsyncSession, records: List[Dict[str, Any]], source: str = "pcc"):
    """將搜尋結果批次寫入 DB (upsert by unit_id+job_number or ezbid_id)"""
    saved = 0
    for r in records:
        try:
            unit_id = r.get("unit_id", "")
            job_number = r.get("job_number", "")
            ezbid_id = r.get("ezbid_id")
            title = r.get("title", "")[:500]

            if not title:
                continue

            # 檢查是否已存在
            if ezbid_id:
                existing = await db.execute(
                    text("SELECT id FROM tender_records WHERE ezbid_id = :eid"),
                    {"eid": str(ezbid_id)}
                )
            elif unit_id and job_number:
                existing = await db.execute(
                    text("SELECT id FROM tender_records WHERE unit_id = :uid AND job_number = :jn"),
                    {"uid": unit_id, "jn": job_number}
                )
            else:
                continue

            if existing.scalar():
                continue  # 已存在，跳過

            # 插入新記錄
            announce = _parse_date(r.get("date", ""))
            budget = _parse_amount(r.get("budget"))

            await db.execute(text("""
                INSERT INTO tender_records (unit_id, job_number, title, unit_name, category,
                    tender_type, budget, announce_date, status, source, ezbid_id, raw_data)
                VALUES (:uid, :jn, :title, :uname, :cat, :type, :budget, :date, :status, :source, :eid, :raw)
            """), {
                "uid": unit_id, "jn": job_number or None, "title": title,
                "uname": r.get("unit_name", "")[:200], "cat": r.get("category", "")[:50],
                "type": r.get("type", "")[:100], "budget": budget,
                "date": announce, "status": r.get("status", "")[:50],
                "source": source, "eid": str(ezbid_id) if ezbid_id else None,
                "raw": json.dumps(r, ensure_ascii=False, default=str)[:2000],
            })

            # 寫入廠商關聯
            record_id = (await db.execute(text("SELECT lastval()"))).scalar()
            if record_id:
                for w in r.get("winner_names", []):
                    if w:
                        await db.execute(text(
                            "INSERT INTO tender_company_links (tender_record_id, company_name, role) VALUES (:rid, :name, 'winner')"
                        ), {"rid": record_id, "name": w[:200]})
                for b in r.get("bidder_names", []):
                    if b:
                        await db.execute(text(
                            "INSERT INTO tender_company_links (tender_record_id, company_name, role) VALUES (:rid, :name, 'bidder')"
                        ), {"rid": record_id, "name": b[:200]})

            saved += 1
        except Exception as e:
            logger.debug(f"Save tender record failed: {e}")
            continue

    if saved > 0:
        await db.commit()
        logger.info(f"Saved {saved} tender records to DB ({source})")

    # Auto-ingest tender entities into Knowledge Graph
    if saved > 0:
        try:
            ingested = await _ingest_tender_entities(db, records)
            if ingested > 0:
                await db.commit()
        except Exception as e:
            logger.debug(f"Tender entity ingestion failed: {e}")

    return saved


async def search_from_db(
    db: AsyncSession, query: str, limit: int = 50,
) -> List[Dict[str, Any]]:
    """從 DB 搜尋標案 — trigram 相似度 + ILIKE，長查詢自動提高門檻

    排序策略：
    1. 完全匹配 title → relevance = 1.0（最高優先）
    2. trigram similarity 降序（短查詢 ≥0.3，長查詢 ≥0.4）
    3. ILIKE substring match
    4. 日期降序

    v5.5.8: 修復長查詢（>20字）回傳過多不相關結果的問題
    """
    from app.services.tender_search_query import build_tender_search_sql
    sql, params = build_tender_search_sql(query, limit=limit)
    result = await db.execute(text(sql), params)

    rows = result.fetchall()
    records = []
    for r in rows:
        winners = [w for w in (r.winners or []) if w] if hasattr(r, 'winners') else []
        bidders = [b for b in (r.bidders or []) if b] if hasattr(r, 'bidders') else []
        records.append({
            "date": str(r.announce_date) if r.announce_date else "",
            "raw_date": int(str(r.announce_date).replace("-", "")) if r.announce_date else 0,
            "title": r.title or "",
            "type": r.tender_type or "",
            "category": r.category or "",
            "unit_id": r.unit_id or "",
            "unit_name": r.unit_name or "",
            "job_number": r.job_number or "",
            "company_names": winners + bidders,
            "company_ids": [],
            "winner_names": winners,
            "bidder_names": bidders,
            "tender_api_url": "",
            "source": r.source or "db",
            "budget": float(r.budget) if r.budget else None,
        })
    return records


async def refresh_pending_tenders(db: AsyncSession, limit: int = 30) -> Dict[str, Any]:
    """定期更新：重查等標期標案的最新狀態 (決標/廢標)"""
    from app.services.tender_search_service import TenderSearchService

    # 找出需要更新的標案：有 job_number、status 非決標、30 天內公告
    rows = await db.execute(text("""
        SELECT id, unit_id, job_number, title, status
        FROM tender_records
        WHERE job_number IS NOT NULL AND job_number != ''
          AND (status IS NULL OR status NOT LIKE '%決標%')
          AND announce_date > CURRENT_DATE - INTERVAL '90 days'
          AND source = 'pcc'
        ORDER BY announce_date DESC
        LIMIT :lim
    """), {"lim": limit})
    pending = rows.fetchall()

    if not pending:
        return {"checked": 0, "updated": 0}

    svc = TenderSearchService()
    updated = 0

    for row in pending:
        try:
            detail = await svc.get_tender_detail(row.unit_id, row.job_number)
            if not detail:
                continue

            new_status = None
            award_amount = None
            for evt in detail.get("events", []):
                t = evt.get("type", "")
                if "決標" in t:
                    new_status = t
                    ad = evt.get("award_details") or {}
                    award_amount = ad.get("total_award_amount")
                elif "無法決標" in t or "廢標" in t:
                    new_status = t

            if new_status and new_status != row.status:
                await db.execute(text("""
                    UPDATE tender_records
                    SET status = :status, award_amount = :award, updated_at = NOW()
                    WHERE id = :id
                """), {"status": new_status, "award": award_amount, "id": row.id})

                # 更新廠商關聯
                for evt in detail.get("events", []):
                    for w in evt.get("companies", []):
                        pass  # companies 在 normalize_detail 中已處理
                # 從 detail events 提取 winner/bidder
                latest = detail.get("latest", {})
                if latest:
                    # 不重複新增已有的廠商
                    existing = await db.execute(text(
                        "SELECT company_name FROM tender_company_links WHERE tender_record_id = :rid"
                    ), {"rid": row.id})
                    existing_names = {r[0] for r in existing.fetchall()}

                    for evt in detail.get("events", []):
                        companies = evt.get("companies", [])
                        if isinstance(companies, list):
                            for c in companies:
                                if c and c not in existing_names:
                                    existing_names.add(c)

                updated += 1
        except Exception:
            continue

    if updated > 0:
        await db.commit()

    return {"checked": len(pending), "updated": updated}


async def build_graph_from_db(db: AsyncSession, query: str, max_tenders: int = 20) -> Dict[str, Any]:
    """從 DB 建構標案知識圖譜 (機關→標案→廠商)"""
    rows = await db.execute(text("""
        SELECT tr.id, tr.title, tr.unit_name, tr.unit_id, tr.job_number, tr.category,
               tr.announce_date, tcl.company_name, tcl.role
        FROM tender_records tr
        LEFT JOIN tender_company_links tcl ON tcl.tender_record_id = tr.id
        WHERE tr.title ILIKE :q OR tr.unit_name ILIKE :q
        ORDER BY tr.announce_date DESC NULLS LAST
        LIMIT :lim
    """), {"q": f"%{query}%", "lim": max_tenders * 3})

    records = rows.fetchall()
    nodes = {}
    edges = []
    tender_ids = set()

    for r in records:
        # 機關節點
        agency_id = f"agency-{r.unit_name or r.unit_id}"
        if agency_id not in nodes:
            nodes[agency_id] = {"id": agency_id, "name": r.unit_name or r.unit_id, "type": "agency"}

        # 標案節點
        tender_id = f"tender-{r.id}"
        if tender_id not in nodes and len(tender_ids) < max_tenders:
            tender_ids.add(r.id)
            nodes[tender_id] = {
                "id": tender_id, "name": (r.title or "")[:40],
                "type": "tender", "category": r.category,
                "date": str(r.announce_date) if r.announce_date else "",
            }
            edges.append({"source": agency_id, "target": tender_id, "relation": "發標"})

        # 廠商節點
        if r.company_name and r.id in tender_ids:
            comp_id = f"company-{r.company_name}"
            if comp_id not in nodes:
                nodes[comp_id] = {"id": comp_id, "name": r.company_name, "type": "company"}
            rel = "得標" if r.role == "winner" else "投標"
            edges.append({"source": tender_id, "target": comp_id, "relation": rel})

    agencies = sum(1 for n in nodes.values() if n["type"] == "agency")
    companies = sum(1 for n in nodes.values() if n["type"] == "company")

    return {
        "query": query,
        "nodes": list(nodes.values()),
        "edges": edges,
        "stats": {"tenders": len(tender_ids), "agencies": agencies, "companies": companies, "edges": len(edges)},
    }


async def cross_reference_pm_cases(db: AsyncSession) -> Dict[str, Any]:
    """跨服務索引：標記已建案的標案"""
    try:
        # 找 PM Cases 的 notes 中含標案案號的
        result = await db.execute(text("""
            UPDATE tender_records tr
            SET status = COALESCE(tr.status, '') || ' [已建案]'
            FROM pm_cases pc
            WHERE pc.notes LIKE '%' || tr.job_number || '%'
              AND tr.job_number IS NOT NULL AND tr.job_number != ''
              AND tr.status NOT LIKE '%已建案%'
            RETURNING tr.id, tr.title, pc.case_code
        """))
        linked = result.fetchall()
        if linked:
            await db.commit()
        return {"linked": len(linked), "cases": [{"title": r[1][:40], "case_code": r[2]} for r in linked[:10]]}
    except Exception as e:
        return {"linked": 0, "error": str(e)[:100]}


async def normalize_company_names(db: AsyncSession) -> Dict[str, Any]:
    """廠商名稱正規化：合併常見變體"""
    # 移除「有限公司」「股份有限公司」等後綴建立 alias 對照
    result = await db.execute(text("""
        SELECT company_name, COUNT(*) as cnt
        FROM tender_company_links
        GROUP BY company_name
        ORDER BY cnt DESC
        LIMIT 50
    """))
    companies = result.fetchall()

    # 找出可能的重複 (名稱前 4 字相同但全名不同)
    from collections import defaultdict
    prefix_groups = defaultdict(list)
    for name, cnt in companies:
        if len(name) >= 4:
            prefix_groups[name[:4]].append({"name": name, "count": cnt})

    duplicates = []
    for prefix, group in prefix_groups.items():
        if len(group) > 1:
            duplicates.append({"prefix": prefix, "variants": group})

    return {"total_companies": len(companies), "potential_duplicates": duplicates}


async def get_db_stats(db: AsyncSession) -> Dict[str, Any]:
    """取得快取統計"""
    total = (await db.execute(text("SELECT COUNT(*) FROM tender_records"))).scalar() or 0
    pcc = (await db.execute(text("SELECT COUNT(*) FROM tender_records WHERE source='pcc'"))).scalar() or 0
    ezbid = (await db.execute(text("SELECT COUNT(*) FROM tender_records WHERE source='ezbid'"))).scalar() or 0
    companies = (await db.execute(text("SELECT COUNT(DISTINCT company_name) FROM tender_company_links"))).scalar() or 0
    latest = (await db.execute(text("SELECT MAX(announce_date) FROM tender_records"))).scalar()
    awarded = (await db.execute(text("SELECT COUNT(*) FROM tender_records WHERE status LIKE '%決標%'"))).scalar() or 0

    return {
        "total_records": total,
        "pcc_records": pcc,
        "ezbid_records": ezbid,
        "awarded_records": awarded,
        "unique_companies": companies,
        "latest_date": str(latest) if latest else None,
    }
