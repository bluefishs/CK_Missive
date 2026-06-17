"""標案詳情 Enrichment（P2）— 2-hop: PCC searchTenderDetail 取點分 orgId → openfun API 取乾淨詳情。

⚠️ 2026-06-17 實測結論（重要）：**PCC 詳情頁有反爬限流**——少量請求後即回精簡 stub 頁
（43-49KB、無 orgId），無論 curl/httpx/補 headers/換 UA。故 2-hop 取 orgId **無法可靠規模化**，
本服務**不掛自動 cron**，僅保留為 best-effort 手動工具（低量、可接受偶發失敗）。可靠的職能
篩選請用確定性自維機制（關鍵字 + 排除 + 承攬史建議，已上線 UI）。詳見 TENDER_RECOMMENDATION_FLOW。
另：使用者瀏覽器點官方直連（searchTenderDetail?pkPmsMain=，原始 '='）不受此限（非我方伺服 IP）。


補齊 tender_records：標的分類(category)、財物採購性質(procurement_nature)、預算(budget NULL 時)、
底價(base_price)、決標(award_result)、廠商(bidders)、org_id。供：
  - 智能職能篩選（採購性質=財物 → 排除儀器/醫療採購；不再靠無窮負面關鍵字）
  - 詳情頁 5 tab 補料 + 官方直連。

設計：
  - 我方 unit_id = PCC pkPmsMain（官方直連已用）。
  - openfun 需點分 orgId（如 A.13.6.20）→ 從 PCC 詳情頁 HTML regex 取得，cache 進 org_id 欄避免重抓。
  - 節流（每案延遲 + 低併發）避免封 IP；只 enrich 推薦/近期標的（非全量）。
  - 任何步驟失敗不擋主流程（保留既有基本欄，記 logger）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PCC_DETAIL_URL = "https://web.pcc.gov.tw/tps/QueryTender/query/searchTenderDetail?pkPmsMain="
OPENFUN_TENDER = "https://pcc-api.openfun.app/api/tender"
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
_ORG_ID_RE = re.compile(r"orgId=([0-9A-Za-z][0-9A-Za-z.]*\.[0-9.]+)")  # 收 A.13.6.20 與 3.5.48 兩式
_THROTTLE_SEC = 0.8  # 每案延遲（禮貌性，避免封 IP）


def _pick(detail: Dict[str, Any], *substrs: str) -> Optional[str]:
    """從 openfun detail dict 取第一個 key 含任一 substr 的值。"""
    for k, v in detail.items():
        if any(s in k for s in substrs) and v not in (None, "", []):
            return str(v).strip()
    return None


def _parse_budget(s: Optional[str]) -> Optional[int]:
    """'1,310,000元' → 1310000。"""
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def _category_from_class(class_str: Optional[str]) -> Optional[str]:
    """標的分類 '勞務類8675-…' → '勞務'；工程類→工程；財物類→財物。"""
    if not class_str:
        return None
    for c in ("工程", "財物", "勞務"):
        if class_str.startswith(c) or f"{c}類" in class_str[:6]:
            return c
    return None


async def _fetch_org_id(client: httpx.AsyncClient, unit_id: str) -> Optional[str]:
    """抓 PCC 詳情頁，regex 取點分 orgId（openfun 查詢用）。"""
    try:
        from urllib.parse import quote
        r = await client.get(PCC_DETAIL_URL + quote(str(unit_id), safe=""), headers=_UA)
        if r.status_code == 200:
            m = _ORG_ID_RE.search(r.text)
            return m.group(1) if m else None
    except Exception as e:
        logger.warning(f"fetch org_id failed unit_id={unit_id}: {e}")
    return None


async def _fetch_openfun_detail(client: httpx.AsyncClient, org_id: str, job_number: str) -> Dict[str, Any]:
    """openfun API → 解析 標的分類/採購性質/預算/底價/決標/廠商。"""
    out: Dict[str, Any] = {}
    try:
        r = await client.get(OPENFUN_TENDER, params={"unit_id": org_id, "job_number": job_number}, headers=_UA)
        if r.status_code != 200:
            return out
        data = r.json()
        bidders: List[str] = []
        for rec in data.get("records", []):
            det = rec.get("detail", {}) or {}
            cls = _pick(det, "標的分類")
            if cls and not out.get("procurement_class"):
                out["procurement_class"] = cls
                out["category"] = _category_from_class(cls)
            nature = _pick(det, "採購性質")
            if nature and not out.get("procurement_nature"):
                out["procurement_nature"] = nature
            bud = _parse_budget(_pick(det, "預算金額"))
            if bud and not out.get("budget"):
                out["budget"] = bud
            bp = _pick(det, "底價金額", "底價")
            if bp and not out.get("base_price"):
                out["base_price"] = bp
            award = _pick(det, "總決標金額", "決標金額")
            if award and not out.get("award_result"):
                out["award_result"] = award
            for k, v in det.items():
                if ("得標廠商" in k or "投標廠商" in k) and v:
                    name = str(v).strip()
                    if name and name not in bidders:
                        bidders.append(name)
        if bidders:
            out["bidders"] = bidders[:20]
    except Exception as e:
        logger.warning(f"fetch openfun detail failed org_id={org_id} job={job_number}: {e}")
    return out


async def enrich_recent(
    db: AsyncSession, days_back: int = 7, limit: int = 60, only_unenriched: bool = True,
) -> Dict[str, int]:
    """批次 enrich 近 N 日標案（節流）。回 {scanned, org_ok, enriched, updated_budget, errors}。"""
    stats = {"scanned": 0, "org_ok": 0, "enriched": 0, "updated_budget": 0, "errors": 0}
    where_unenriched = "AND detail_enriched_at IS NULL" if only_unenriched else ""
    rows = (await db.execute(text(f"""
        SELECT id, unit_id, job_number, org_id, budget
        FROM tender_records
        WHERE announce_date >= (CURRENT_DATE - :db_days * INTERVAL '1 day')::date
          AND COALESCE(tender_type, '') NOT LIKE '%決標%'
          AND unit_id IS NOT NULL AND job_number IS NOT NULL AND job_number <> ''
          {where_unenriched}
        ORDER BY announce_date DESC
        LIMIT :lim
    """), {"db_days": days_back, "lim": limit})).fetchall()
    stats["scanned"] = len(rows)
    if not rows:
        return stats

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for r in rows:
            try:
                org_id = r.org_id or await _fetch_org_id(client, r.unit_id)
                if not org_id:
                    stats["errors"] += 1
                    # 仍標記嘗試過（避免每日重撞），但不寫 enriched 欄
                    await db.execute(text("UPDATE tender_records SET detail_enriched_at=:now WHERE id=:id"),
                                     {"now": datetime.now(), "id": r.id})
                    await asyncio.sleep(_THROTTLE_SEC)
                    continue
                stats["org_ok"] += 1
                det = await _fetch_openfun_detail(client, org_id, r.job_number)
                # UPDATE（budget 僅在原為 NULL 時補；category/性質/底價/決標/廠商補值）
                await db.execute(text("""
                    UPDATE tender_records SET
                        org_id = :org_id,
                        category = COALESCE(NULLIF(:category,''), category),
                        procurement_nature = COALESCE(NULLIF(:nature,''), procurement_nature),
                        budget = CASE WHEN budget IS NULL AND :budget IS NOT NULL THEN :budget ELSE budget END,
                        base_price = COALESCE(NULLIF(:base_price,''), base_price),
                        award_result = COALESCE(NULLIF(:award,''), award_result),
                        bidders = COALESCE(:bidders, bidders),
                        detail_enriched_at = :now
                    WHERE id = :id
                """), {
                    "org_id": org_id,
                    "category": det.get("category") or "",
                    "nature": det.get("procurement_nature") or "",
                    "budget": det.get("budget"),
                    "base_price": det.get("base_price") or "",
                    "award": det.get("award_result") or "",
                    "bidders": json.dumps(det.get("bidders"), ensure_ascii=False) if det.get("bidders") else None,
                    "now": datetime.now(),
                    "id": r.id,
                })
                stats["enriched"] += 1
                if r.budget is None and det.get("budget"):
                    stats["updated_budget"] += 1
            except Exception as e:
                logger.warning(f"enrich tender id={r.id} failed: {e}")
                stats["errors"] += 1
            await asyncio.sleep(_THROTTLE_SEC)
        await db.commit()
    logger.info(f"tender enrich_recent done: {stats}")
    return stats
