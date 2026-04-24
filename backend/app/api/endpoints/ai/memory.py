# -*- coding: utf-8 -*-
"""Memory Wiki API 端點 — /api/ai/memory/*

2026-04-19 Memory Wiki Phase 5 (切片 1): 後端 API。

端點分類：
- Diary: 讀今日/指定日期 diary
- Patterns/Failures: 列表 + 詳情
- Proposals: 列表 + approve/reject
- Crystals: 列表 + rollback
- Autobiography: 最新 + 歷史
- Nebula: 技能星雲 graph 資料
- Stats: Memory 總覽

全部 POST + require_auth（敏感操作額外 require_admin）。
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date as date_type, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

from app.core.dependencies import require_admin, require_auth

logger = logging.getLogger(__name__)
TZ_TAIPEI = ZoneInfo("Asia/Taipei")

router = APIRouter(dependencies=[Depends(require_auth())])


# ────────── Paths（複用既有 constants）──────────

PROJECT_ROOT = Path(__file__).resolve().parents[5]
WIKI_MEMORY = PROJECT_ROOT / "wiki" / "memory"
DIARY_DIR = WIKI_MEMORY / "diary"
PATTERNS_DIR = WIKI_MEMORY / "patterns"
FAILURES_DIR = WIKI_MEMORY / "failures"
PROPOSALS_DIR = WIKI_MEMORY / "proposals"
CRYSTALS_DIR = WIKI_MEMORY / "crystals"
EVOLUTIONS_DIR = WIKI_MEMORY / "evolutions"


# ────────── Schemas ──────────

class DiaryQueryReq(BaseModel):
    date: Optional[str] = Field(None, description="YYYY-MM-DD；None 為今日")


class ListReq(BaseModel):
    limit: int = 50
    offset: int = 0


class ApproveReq(BaseModel):
    proposal_id: str
    approved_by: str = "admin"


class RejectReq(BaseModel):
    proposal_id: str
    reason: str = ""
    rejected_by: str = "admin"


class RollbackReq(BaseModel):
    crystal_id: str


class NebulaReq(BaseModel):
    days: int = 30


# ────────── Helpers ──────────

def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """Extract simple scalar values from YAML frontmatter."""
    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        return {}
    fm = fm_match.group(1)
    meta: Dict[str, Any] = {}
    for line in fm.splitlines():
        m = re.match(r"^([a-zA-Z_][\w]*?):\s*(.+?)\s*$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            # 嘗試解析為 int/float/bool
            if val.isdigit():
                meta[key] = int(val)
            elif re.match(r"^-?\d+\.\d+$", val):
                meta[key] = float(val)
            elif val.lower() in ("true", "false"):
                meta[key] = val.lower() == "true"
            elif val.startswith("[") and val.endswith("]"):
                try:
                    meta[key] = json.loads(val)
                except Exception:
                    meta[key] = val
            else:
                meta[key] = val
    return meta


def _read_md_summary(path: Path) -> Dict[str, Any]:
    """Read .md file, return {meta: frontmatter, body_preview: first 300 chars}."""
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
        return {
            "filename": path.name,
            "meta": meta,
            "body_preview": body[:500].strip(),
            "size_bytes": path.stat().st_size,
            "mtime": datetime.fromtimestamp(path.stat().st_mtime, tz=TZ_TAIPEI).isoformat(),
        }
    except Exception as e:
        logger.warning("Read %s failed: %s", path.name, e)
        return {}


def _list_dir_summaries(
    directory: Path, pattern: str = "*.md", limit: int = 50, offset: int = 0,
    sort_key: str = "mtime", reverse: bool = True,
) -> List[Dict[str, Any]]:
    """List all .md files in dir, sorted by mtime desc."""
    if not directory.exists():
        return []
    files = list(directory.glob(pattern))
    # 排除 .gitkeep 等
    files = [f for f in files if not f.name.startswith(".")]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=reverse)
    return [_read_md_summary(f) for f in files[offset:offset + limit]]


# ────────── Diary ──────────

@router.post("/memory/diary/date")
async def memory_diary_by_date(req: DiaryQueryReq):
    """讀指定日期 diary（None 為今日）。"""
    from app.services.memory.diary_service import today_date

    if req.date:
        try:
            target = date_type.fromisoformat(req.date)
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    else:
        target = today_date()

    path = DIARY_DIR / f"{target.isoformat()}.md"
    if not path.exists():
        return {"success": True, "data": None, "message": f"無 {target} 日記"}
    return {
        "success": True,
        "data": _read_md_summary(path),
    }


@router.post("/memory/diary/recent")
async def memory_diary_recent(req: ListReq):
    """列最近 N 日 diary。"""
    items = _list_dir_summaries(DIARY_DIR, limit=req.limit, offset=req.offset)
    return {"success": True, "data": items, "total": len(items)}


@router.post("/memory/anti-echo/recent")
async def memory_anti_echo_recent(req: ListReq):
    """列近 N 天 diary 中的反迴聲室觸發段落（v5.8.3 坤哥對外展示）。

    前端 IdentityTab / Header 用於呈現「坤哥最近的自我質疑」。
    格式：{date, time, reflections: [...], reason: 觸發原因}
    """
    import re as _re
    if not DIARY_DIR.exists():
        return {"success": True, "data": [], "total": 0}

    paths = sorted(DIARY_DIR.glob("*.md"), key=lambda p: p.name, reverse=True)[:14]
    blocks: List[Dict[str, Any]] = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        # 找 `## HH:MM:SS — 🔔 反迴聲室` 開頭至下一個 `## ` 之前
        pattern = _re.compile(
            r"^## (\d{2}:\d{2}:\d{2}) — 🔔 反迴聲室[^\n]*\n(.*?)(?=\n## |\Z)",
            _re.MULTILINE | _re.DOTALL,
        )
        for m in pattern.finditer(text):
            body = m.group(2).strip()
            # 解析觸發原因 + 候選
            reason_m = _re.search(r"\*\*觸發\*\*：([^\n]+)", body)
            reason = reason_m.group(1).strip() if reason_m else ""
            reflections = _re.findall(r"^\d+\.\s+([^\n]+)", body, _re.MULTILINE)
            blocks.append({
                "date": p.stem,
                "time": m.group(1),
                "reason": reason,
                "reflections": reflections,
                "body_preview": body[:400],
            })
    # 最近優先
    blocks.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
    return {
        "success": True,
        "data": blocks[req.offset:req.offset + req.limit],
        "total": len(blocks),
    }


# ────────── Patterns / Failures ──────────

@router.post("/memory/patterns/list")
async def memory_patterns_list(req: ListReq):
    items = _list_dir_summaries(PATTERNS_DIR, "pattern-*.md", req.limit, req.offset)
    return {"success": True, "data": items, "total": len(items)}


@router.post("/memory/failures/list")
async def memory_failures_list(req: ListReq):
    items = _list_dir_summaries(FAILURES_DIR, "failure-*.md", req.limit, req.offset)
    return {"success": True, "data": items, "total": len(items)}


# ────────── Proposals (admin for approve/reject) ──────────

@router.post("/memory/proposals/list")
async def memory_proposals_list(req: ListReq):
    items = _list_dir_summaries(PROPOSALS_DIR, "*.md", req.limit, req.offset)
    # 只要 pending（可在前端 filter，此處先全回）
    return {"success": True, "data": items, "total": len(items)}


@router.post("/memory/proposals/approve")
async def memory_proposals_approve(req: ApproveReq, _admin=Depends(require_admin())):
    """批准 proposal → CrystalApplier.apply_proposal（Admin 限定）。"""
    from app.services.memory.crystal_applier import CrystalApplier

    applier = CrystalApplier()
    result = await applier.apply_proposal(req.proposal_id, approved_by=req.approved_by)

    if not result.ok:
        return {
            "success": False,
            "error": result.error,
            "snapshot": str(result.snapshot_path) if result.snapshot_path else None,
        }
    return {
        "success": True,
        "data": {
            "crystal_id": result.crystal_id,
            "snapshot": str(result.snapshot_path) if result.snapshot_path else None,
        },
    }


@router.post("/memory/proposals/reject")
async def memory_proposals_reject(req: RejectReq, _admin=Depends(require_admin())):
    """拒絕 proposal — 標記狀態，7 日內不重複提案。"""
    path = PROPOSALS_DIR / f"{req.proposal_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Proposal not found")

    try:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^status:\s*\S+", "status: rejected", text, count=1, flags=re.MULTILINE)
        # 追加 rejected_at + reason 到 frontmatter
        text = re.sub(
            r"(^---\s*\n.*?)(\n---\s*\n)",
            rf"\1\nrejected_at: {datetime.now(TZ_TAIPEI).isoformat()}\nrejected_by: "
            rf"{req.rejected_by}\nreject_reason: {json.dumps(req.reason, ensure_ascii=False)}\2",
            text, count=1, flags=re.DOTALL,
        )
        path.write_text(text, encoding="utf-8")
        return {"success": True, "data": {"proposal_id": req.proposal_id, "status": "rejected"}}
    except Exception as e:
        logger.error("Reject proposal failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ────────── Crystals ──────────

@router.post("/memory/crystals/list")
async def memory_crystals_list(req: ListReq):
    items = _list_dir_summaries(CRYSTALS_DIR, "crystal-*.md", req.limit, req.offset)
    return {"success": True, "data": items, "total": len(items)}


@router.post("/memory/crystals/rollback")
async def memory_crystals_rollback(
    req: RollbackReq, _admin=Depends(require_admin()),
):
    """回滾指定 crystal（還原 yaml snapshot）。"""
    from app.services.memory.crystal_applier import CrystalApplier

    applier = CrystalApplier()
    r = await applier.rollback(req.crystal_id)
    if not r.ok:
        return {"success": False, "error": r.error}
    return {"success": True, "data": {"crystal_id": r.crystal_id, "rolled_back": True}}


# ────────── Autobiography ──────────

@router.post("/memory/autobiography/latest")
async def memory_autobiography_latest():
    """取最新一份週自傳。"""
    if not EVOLUTIONS_DIR.exists():
        return {"success": True, "data": None}
    files = sorted(
        EVOLUTIONS_DIR.glob("20*-W*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return {"success": True, "data": None}
    return {"success": True, "data": _read_md_summary(files[0])}


@router.post("/memory/autobiography/list")
async def memory_autobiography_list(req: ListReq):
    """列歷史週自傳。"""
    items = _list_dir_summaries(EVOLUTIONS_DIR, "20*-W*.md", req.limit, req.offset)
    return {"success": True, "data": items, "total": len(items)}


# ────────── Nebula (星雲) ──────────

@router.post("/memory/nebula/graph")
async def memory_nebula_graph(req: NebulaReq):
    """回傳技能星雲 graph（nodes + edges）供前端 force-graph 渲染。

    節點 = pattern（含 tool_sequence / 熟練度）
    邊 = pattern 間的 tool 交集（越多共用 tool 越近）
    """
    if not PATTERNS_DIR.exists():
        return {"success": True, "data": {"nodes": [], "edges": []}}

    nodes: List[Dict[str, Any]] = []
    tool_to_patterns: Dict[str, List[str]] = {}

    for path in PATTERNS_DIR.glob("pattern-*.md"):
        meta = _parse_frontmatter(path.read_text(encoding="utf-8"))
        if not meta.get("template_hash"):
            continue
        t_hash = meta["template_hash"]
        hit = meta.get("hit_count", 0) or 0
        success_rate = meta.get("success_rate", 0.0) or 0.0
        tools = meta.get("tool_sequence", []) or []
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except Exception:
                tools = []
        domains = meta.get("domains", []) or []

        nodes.append({
            "id": t_hash,
            "label": f"{'+'.join(tools[:2])}{'...' if len(tools) > 2 else ''}",
            "tools": tools,
            "domains": domains,
            "hit_count": hit,
            "success_rate": round(success_rate, 3),
            "size": min(40, max(5, hit)),  # 視覺大小
            "color": _domain_color(domains[0] if domains else "mixed"),
            "is_crystal": meta.get("crystallization_candidate", False),
        })
        for tool in tools:
            tool_to_patterns.setdefault(tool, []).append(t_hash)

    # 建 edge：共用 tool 的 pattern 互連
    edges: List[Dict[str, Any]] = []
    edge_set = set()
    for tool, p_list in tool_to_patterns.items():
        if len(p_list) < 2:
            continue
        for i in range(len(p_list)):
            for j in range(i + 1, len(p_list)):
                key = tuple(sorted([p_list[i], p_list[j]]))
                if key not in edge_set:
                    edge_set.add(key)
                    edges.append({
                        "source": key[0], "target": key[1],
                        "label": tool, "weight": 1,
                    })
                else:
                    # 累積 weight（更多共用 tool 邊更粗）
                    for e in edges:
                        if {e["source"], e["target"]} == set(key):
                            e["weight"] += 1

    return {
        "success": True,
        "data": {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "crystal_count": sum(1 for n in nodes if n.get("is_crystal")),
            },
        },
    }


def _domain_color(domain: str) -> str:
    """domain → hex color（供前端）。"""
    colors = {
        "doc": "#1890ff",        # blue
        "dispatch": "#52c41a",   # green
        "graph": "#722ed1",      # purple
        "analysis": "#faad14",   # gold
        "pm": "#13c2c2",         # cyan
        "erp": "#eb2f96",        # magenta
        "mixed": "#8c8c8c",      # gray
    }
    return colors.get(domain, "#8c8c8c")


# ────────── Stats 總覽（Dashboard 首頁） ──────────

@router.post("/memory/stats")
async def memory_stats():
    """Memory Wiki 整體統計。"""
    def _count_files(d: Path, pattern: str = "*.md") -> int:
        if not d.exists():
            return 0
        return len([f for f in d.glob(pattern) if not f.name.startswith(".")])

    def _count_pending_proposals() -> int:
        if not PROPOSALS_DIR.exists():
            return 0
        cnt = 0
        for p in PROPOSALS_DIR.glob("*.md"):
            try:
                if "status: pending" in p.read_text(encoding="utf-8"):
                    cnt += 1
            except Exception:
                pass
        return cnt

    data = {
        "diary_days": _count_files(DIARY_DIR),
        "patterns": _count_files(PATTERNS_DIR, "pattern-*.md"),
        "failures": _count_files(FAILURES_DIR, "failure-*.md"),
        "crystals": _count_files(CRYSTALS_DIR, "crystal-*.md"),
        "proposals_total": _count_files(PROPOSALS_DIR),
        "proposals_pending": _count_pending_proposals(),
        "evolutions": _count_files(EVOLUTIONS_DIR, "20*-W*.md"),
    }

    # Prometheus gauges refresh（best-effort）
    try:
        from app.core.memory_wiki_metrics import get_memory_wiki_metrics
        get_memory_wiki_metrics().refresh_from_disk(WIKI_MEMORY)
    except Exception as e:
        logger.debug("Memory wiki metrics refresh failed: %s", e)

    return {"success": True, "data": data}
