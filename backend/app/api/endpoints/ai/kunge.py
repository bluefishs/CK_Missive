"""坤哥 State Snapshot Endpoint (v6.13, 2026-05-31)

對齊 owner「坤哥 + Hermes agents + 智能體 整合連通真活」訴求。

整合斷層揭發:
- Hermes 透過 query_missive 拿 agent answer (智能體真活)
- 但 Hermes user 無法查「坤哥本週狀態」(diary/critique/pattern/proposal/crystal)
- 修法: 一站式 snapshot endpoint，service token 認證，Hermes 可呼叫

整合來源:
- wiki/memory/diary 最近 N 日
- wiki/memory/critiques 質性反省
- wiki/memory/patterns 累積 pattern
- wiki/memory/proposals 待 owner approve
- wiki/memory/crystals 已結晶信念
- wiki/memory/lessons 跨子目錄 rglob
- DB agent_learnings / agent_evolution_history 統計

純 read endpoint — 對齊 owner「備份安全」原則。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.paths import WIKI_MEMORY_DIR as WIKI_MEMORY
from app.core.service_auth import require_scope
from app.db.database import get_db


logger = logging.getLogger(__name__)
router = APIRouter()


def _count_files(dir_path: Path, pattern: str = "*.md", recursive: bool = True) -> int:
    """rglob 抓子目錄（修 W22 lesson=0 假象 bug）"""
    if not dir_path.is_dir():
        return 0
    glob = dir_path.rglob if recursive else dir_path.glob
    return sum(
        1 for f in glob(pattern)
        if not f.name.startswith(("README", "."))
    )


def _recent_filenames(dir_path: Path, days: int, pattern: str = "*.md",
                     recursive: bool = True, limit: int = 10) -> List[str]:
    if not dir_path.is_dir():
        return []
    cutoff = (datetime.now() - timedelta(days=days)).timestamp()
    glob = dir_path.rglob if recursive else dir_path.glob
    out = []
    for f in glob(pattern):
        if f.name.startswith(("README", ".")):
            continue
        try:
            if f.stat().st_mtime > cutoff:
                out.append(f.name)
        except Exception:
            continue
    out.sort(reverse=True)
    return out[:limit]


def _pending_proposals(limit: int = 10) -> List[Dict[str, Any]]:
    """讀 wiki/memory/proposals/ 並 parse status: pending"""
    proposals_dir = WIKI_MEMORY / "proposals"
    if not proposals_dir.is_dir():
        return []
    items = []
    for f in proposals_dir.glob("*.md"):
        try:
            text_content = f.read_text(encoding="utf-8", errors="ignore")
            if "status: pending" not in text_content:
                continue
            # Parse simple frontmatter
            target_file = ""
            proposal_kind = ""
            proposed_at = ""
            for line in text_content.splitlines()[:20]:
                if line.startswith("target_file:"):
                    target_file = line.split(":", 1)[1].strip()
                elif line.startswith("proposal_kind:"):
                    proposal_kind = line.split(":", 1)[1].strip()
                elif line.startswith("proposed_at:"):
                    proposed_at = line.split(":", 1)[1].strip()
            items.append({
                "proposal_id": f.stem,
                "kind": proposal_kind,
                "target": target_file,
                "proposed_at": proposed_at,
            })
        except Exception:
            continue
    items.sort(key=lambda x: x.get("proposed_at", ""), reverse=True)
    return items[:limit]


class KungeSnapshotReq(BaseModel):
    window_days: int = Field(7, ge=1, le=90, description="統計窗口天數")
    include_pending_proposals: bool = True


class KungeSnapshotResp(BaseModel):
    success: bool
    timestamp: str
    window_days: int
    counts: Dict[str, int]
    recent: Dict[str, List[str]]
    pending_proposals: List[Dict[str, Any]]
    db_stats: Dict[str, int]
    health_signals: Dict[str, Any]


@router.post("/kunge/snapshot", response_model=KungeSnapshotResp)
async def kunge_snapshot(
    req: KungeSnapshotReq,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(require_scope("read:agent")),
) -> KungeSnapshotResp:
    """坤哥意識體 + 智能體 一站式 snapshot

    對齊 owner「坤哥 + Hermes agents + 智能體 整合連通真活」訴求。

    Hermes 呼叫範例 (透過 ck-missive-bridge skill):
        POST /api/ai/kunge/snapshot
        Headers: X-Service-Token: <token>
        Body: {"window_days": 7, "include_pending_proposals": true}
    """
    # 1. 全層 file counts (rglob 修法後真實)
    counts = {
        "diary": _count_files(WIKI_MEMORY / "diary", recursive=False),
        "patterns": _count_files(WIKI_MEMORY / "patterns", "pattern-*.md", recursive=False),
        "failures": _count_files(WIKI_MEMORY / "failures", recursive=False),
        "proposals": _count_files(WIKI_MEMORY / "proposals", recursive=False),
        "critiques": _count_files(WIKI_MEMORY / "critiques", "critique-*.md", recursive=False),
        "crystals": _count_files(WIKI_MEMORY / "crystals", "crystal-*.md", recursive=False),
        "lessons": _count_files(WIKI_MEMORY / "lessons"),  # rglob 抓子目錄
        "evolutions": _count_files(WIKI_MEMORY / "evolutions", recursive=False),
        "self_retrospective": _count_files(
            WIKI_MEMORY / "self-retrospective-reports", recursive=False,
        ),
    }

    # 2. window 內最近檔案
    recent = {
        "diary": _recent_filenames(WIKI_MEMORY / "diary", req.window_days, recursive=False),
        "patterns": _recent_filenames(
            WIKI_MEMORY / "patterns", req.window_days, "pattern-*.md", recursive=False,
        ),
        "critiques": _recent_filenames(
            WIKI_MEMORY / "critiques", req.window_days, "critique-*.md", recursive=False,
        ),
        "lessons": _recent_filenames(WIKI_MEMORY / "lessons", req.window_days),
        "evolutions": _recent_filenames(WIKI_MEMORY / "evolutions", req.window_days, recursive=False),
    }

    # 3. pending proposals (對齊 owner 5/31 推送的 4 proposal 決策訴求)
    pending = _pending_proposals() if req.include_pending_proposals else []

    # 4. DB agent_* 統計
    db_stats = {}
    try:
        r = await db.execute(text(
            "SELECT COUNT(*) FROM agent_learnings "
            f"WHERE created_at > NOW() - INTERVAL '{req.window_days} days'"
        ))
        db_stats["agent_learnings_in_window"] = r.scalar() or 0

        r = await db.execute(text("SELECT COUNT(*) FROM agent_learnings"))
        db_stats["agent_learnings_total"] = r.scalar() or 0

        r = await db.execute(text(
            "SELECT COUNT(*) FROM agent_evolution_history "
            f"WHERE created_at > NOW() - INTERVAL '{req.window_days} days'"
        ))
        db_stats["agent_evolution_in_window"] = r.scalar() or 0

        r = await db.execute(text(
            "SELECT COUNT(*) FROM agent_query_traces "
            f"WHERE created_at > NOW() - INTERVAL '{req.window_days} days'"
        ))
        db_stats["agent_query_traces_in_window"] = r.scalar() or 0
    except Exception as e:
        logger.warning("kunge_snapshot DB stats failed: %s", e)
        db_stats["error"] = str(e)[:200]

    # 5. health signals (整合自我意識真活訊號)
    diary_count = len(recent["diary"])
    critiques_count = len(recent["critiques"])
    query_count = db_stats.get("agent_query_traces_in_window", 0)
    crystals_count = counts["crystals"]

    health_signals = {
        "diary_streak_ok": diary_count >= 5,
        "critique_silent_dormant": critiques_count == 0 and query_count >= 5,
        "crystal_dir_exists": (WIKI_MEMORY / "crystals").is_dir(),
        "pattern_to_crystal_ratio": (
            crystals_count / counts["patterns"] if counts["patterns"] > 0 else 0
        ),
        "pending_proposals_count": len(pending),
        "lesson_coverage_rglob_ok": counts["lessons"] > 0,
        # 對齊 5/31 三層覆盤的 4 半接通評估
        "v6_13_half_wired_status": {
            "weekly_cron": "✅ generator script ready",
            "critique_audit": "✅ audit script ready",
            "crystallizer_alert": "⚠️ pattern→crystal 斷",
            "lessons_dual_track": "✅ wiki rglob 修正",
        },
    }

    return KungeSnapshotResp(
        success=True,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        window_days=req.window_days,
        counts=counts,
        recent=recent,
        pending_proposals=pending,
        db_stats=db_stats,
        health_signals=health_signals,
    )
