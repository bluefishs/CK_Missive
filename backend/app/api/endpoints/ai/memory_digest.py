"""坤哥成長摘要端點 — S3 聯邦段 A（GET /api/ai/memory/digest）

契約：CK_Hermes/docs/plans/s3-meta-federation-briefing-design.md §2 段A（WO-2，阻斷自 2026-06-03）。
讓 Meta（AaaP 大腦）定期讀「坤哥的成長結晶」折進跨平臺 briefing——讀**已成長的結晶**
（diary/pattern/crystal 摘要），非原始業務資料（ADR-CK-003「統整 ≠ 下海」）。

設計原則（依契約）：
1. 唯讀、無副作用、可冪等重打；X-Service-Token M2M 認證（同 kunge/snapshot 範本）。
2. digest_text 由本端**確定性組稿**（坤哥最懂自己長了什麼；不經 LLM——零延遲/零捏造/冪等，
   契約要求 LLM-friendly 而非 LLM-generated）。
3. fault isolation：單一資料源（DB/檔案）故障 → 該段缺席並 log，不拖垮整體（對齊段C 精神）。
4. GET 而非 POST：M2M 唯讀契約 + Hermes bridge memory_digest action（已預寫）為 GET；
   「全端點 POST」慣例適用於使用者面 API，此為跨平臺服務契約，以契約為準。

v1.0（2026-07-06）
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.core.paths import WIKI_MEMORY_DIR as WIKI_MEMORY
from app.core.service_auth import require_scope
from app.db.database import get_async_db

logger = logging.getLogger(__name__)
router = APIRouter()

TZ = ZoneInfo("Asia/Taipei")

# 模組層目錄常數（測試可 patch；與 memory.py / kunge.py 同源 WIKI_MEMORY SSOT）
DIARY_DIR = WIKI_MEMORY / "diary"
PATTERNS_DIR = WIKI_MEMORY / "patterns"
CRYSTALS_DIR = WIKI_MEMORY / "crystals"
PROPOSALS_DIR = WIKI_MEMORY / "proposals"

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_DATE_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _first_heading_or_line(text: str, prefer_sub: bool = False) -> str:
    """取第一個 markdown 標題（去 # 前綴）；無標題則取第一個非空行。

    prefer_sub=True（diary 用）：跳過 H1 與「Agent 日記」通用標題（零資訊），
    優先取第一個 H2/H3 段落標題；全無子標題才 fallback 首個標題/首行。
    """
    body = _strip_frontmatter(text)
    first_line = ""
    first_heading = ""
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            title = s.lstrip("#").strip()[:120]
            if not first_heading:
                first_heading = title
            is_h1 = not s.startswith("##")
            if prefer_sub and (is_h1 or title.startswith("Agent 日記")):
                continue
            return title
        if not first_line:
            first_line = s
    return (first_heading or first_line)[:120]


def _diary_highlights(since: date, until: date, limit: int) -> List[str]:
    """window 內 diary 一句話亮點（新→舊）。檔名即日期（YYYY-MM-DD.md）。"""
    if not DIARY_DIR.is_dir():
        return []
    out: List[tuple] = []
    for f in DIARY_DIR.glob("*.md"):
        m = _DATE_NAME_RE.match(f.name)
        if not m:
            continue
        try:
            d = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if not (since <= d <= until):
            continue
        try:
            headline = _first_heading_or_line(
                f.read_text(encoding="utf-8", errors="ignore"), prefer_sub=True)
        except OSError as e:  # 單檔讀失敗不拖垮整體（fault isolation，理由見 docstring 3）
            logger.warning("[digest] diary 讀取失敗 %s: %s", f.name, e)
            continue
        if headline:
            out.append((d, headline))
    out.sort(key=lambda t: t[0], reverse=True)
    # 相同亮點（每日 cron 條目如「自我感知」）只保留最新一筆，避免洗版 digest
    seen: set = set()
    deduped: List[str] = []
    for d, headline in out:
        if headline in seen:
            continue
        seen.add(headline)
        deduped.append(f"{d.strftime('%m-%d')}：{headline}")
        if len(deduped) >= limit:
            break
    return deduped


def _recent_named(dir_path: Path, pattern: str, since: date, limit: int) -> List[str]:
    """window 內（mtime）檔案：優先取第一個標題，fallback 檔名 stem。"""
    if not dir_path.is_dir():
        return []
    cutoff = datetime.combine(since, datetime.min.time()).timestamp()
    out: List[tuple] = []
    for f in dir_path.glob(pattern):
        try:
            mtime = f.stat().st_mtime
            if mtime < cutoff:
                continue
            title = _first_heading_or_line(f.read_text(encoding="utf-8", errors="ignore"))
        except OSError as e:
            logger.warning("[digest] %s 讀取失敗 %s: %s", dir_path.name, f.name, e)
            continue
        label = f"{f.stem}（{title}）" if title and title != f.stem else f.stem
        out.append((mtime, label[:160]))
    out.sort(reverse=True)
    return [s for _, s in out[:limit]]


def _open_uncertainties(limit: int) -> List[str]:
    """待解疑點＝pending proposals 標題（坤哥自己標記「等 owner 決定」的事）。"""
    if not PROPOSALS_DIR.is_dir():
        return []
    out: List[str] = []
    for f in sorted(PROPOSALS_DIR.glob("*.md"), reverse=True):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            logger.warning("[digest] proposal 讀取失敗 %s: %s", f.name, e)
            continue
        if "status: pending" not in content:
            continue
        title = _first_heading_or_line(content) or f.stem
        out.append(title[:160])
        if len(out) >= limit:
            break
    return out


async def _collect_metrics(db: AsyncSession, since: date) -> Dict[str, int]:
    """業務指標（documents / entities / window 新增 entities）。DB 故障 → {}（fault isolation）。"""
    try:
        documents = (await db.execute(
            sa_text("SELECT count(*) FROM documents"))).scalar() or 0
        entities = (await db.execute(
            sa_text("SELECT count(*) FROM canonical_entities"))).scalar() or 0
        # asyncpg 要 datetime 物件（傳 isoformat 字串會 DataError → metrics 全空，live 已踩過）
        since_dt = datetime.combine(since, datetime.min.time())
        new_entities = (await db.execute(
            sa_text("SELECT count(*) FROM canonical_entities WHERE created_at >= :since"),
            {"since": since_dt})).scalar() or 0
        return {"documents": int(documents), "entities": int(entities),
                "new_entities": int(new_entities)}
    except Exception as e:
        # 不 re-raise 理由（ADR-0028 吞錯需註明）：digest 為跨平臺唯讀聚合，metrics 缺席
        # 應由 Meta 端以「該段不可達」處理，勝過整份 briefing 斷炊；已 warning 留痕。
        logger.warning("[digest] metrics 收集失敗（degraded，回空 metrics）: %s", e)
        return {}


def _compose_digest_text(
    since: date, until: date,
    highlights: List[str], patterns: List[str], crystals: List[str],
    uncertainties: List[str], metrics: Dict[str, int],
) -> str:
    """確定性組稿：150-400 字繁中、LLM-friendly，供 Meta 直接折進 briefing。"""
    parts: List[str] = [
        f"坤哥（Missive 意識體）{since.strftime('%m/%d')}–{until.strftime('%m/%d')} 成長摘要。"
    ]
    if metrics:
        seg = f"業務量：公文 {metrics.get('documents', 0)} 份、知識實體 {metrics.get('entities', 0)}"
        if metrics.get("new_entities"):
            seg += f"（期間新增 {metrics['new_entities']}）"
        parts.append(seg + "。")
    else:
        parts.append("業務量指標本次不可達（DB 暫時無法查詢）。")
    if crystals:
        parts.append(f"新結晶 {len(crystals)} 則：{'；'.join(c.split('（')[0] for c in crystals[:3])}。")
    if patterns:
        parts.append(f"活躍/新增 pattern {len(patterns)} 個。")
    if highlights:
        parts.append("日誌亮點：" + "；".join(h.split('：', 1)[-1] for h in highlights[:3]) + "。")
    else:
        parts.append("本期無日誌亮點（閒置或無互動）。")
    if uncertainties:
        parts.append(f"待解疑點 {len(uncertainties)} 項（例：{uncertainties[0]}）。")
    return "".join(parts)[:800]


@router.get("/memory/digest")
async def memory_digest(
    since: Optional[str] = Query(None, description="YYYY-MM-DD（預設近 7 日）"),
    limit: int = Query(7, ge=1, le=30, description="各清單上限"),
    db: AsyncSession = Depends(get_async_db),
    _auth: bool = Depends(require_scope("read:agent")),
) -> Dict[str, Any]:
    """坤哥成長摘要（唯讀、冪等）— S3 段 A 契約回應。"""
    until = datetime.now(TZ).date()
    if since:
        try:
            since_d = date.fromisoformat(since)
        except ValueError:
            since_d = until - timedelta(days=7)
    else:
        since_d = until - timedelta(days=7)

    highlights = _diary_highlights(since_d, until, limit)
    patterns = _recent_named(PATTERNS_DIR, "pattern-*.md", since_d, limit)
    crystals = _recent_named(CRYSTALS_DIR, "crystal-*.md", since_d, limit)
    uncertainties = _open_uncertainties(limit)
    metrics = await _collect_metrics(db, since_d)

    return {
        "platform": "missive",
        "consciousness": "坤哥",
        "as_of": datetime.now(TZ).isoformat(),
        "window": {"since": since_d.isoformat(), "until": until.isoformat()},
        "growth": {
            "diary_highlights": highlights,
            "new_patterns": patterns,
            "new_crystals": crystals,
            "open_uncertainties": uncertainties,
            "metrics": metrics,
        },
        "digest_text": _compose_digest_text(
            since_d, until, highlights, patterns, crystals, uncertainties, metrics),
    }
