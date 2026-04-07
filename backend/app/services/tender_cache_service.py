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

    return saved


async def get_db_stats(db: AsyncSession) -> Dict[str, Any]:
    """取得快取統計"""
    total = (await db.execute(text("SELECT COUNT(*) FROM tender_records"))).scalar() or 0
    pcc = (await db.execute(text("SELECT COUNT(*) FROM tender_records WHERE source='pcc'"))).scalar() or 0
    ezbid = (await db.execute(text("SELECT COUNT(*) FROM tender_records WHERE source='ezbid'"))).scalar() or 0
    companies = (await db.execute(text("SELECT COUNT(DISTINCT company_name) FROM tender_company_links"))).scalar() or 0
    latest = (await db.execute(text("SELECT MAX(announce_date) FROM tender_records"))).scalar()

    return {
        "total_records": total,
        "pcc_records": pcc,
        "ezbid_records": ezbid,
        "unique_companies": companies,
        "latest_date": str(latest) if latest else None,
    }
