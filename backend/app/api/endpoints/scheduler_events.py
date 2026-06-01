"""Scheduler events & retrospective reports endpoints (v6.13, 2026-05-31)

Owner: 前端需提供專案排程紀錄追溯表 + 覆盤紀錄

提供 2 endpoint:
- GET /admin/scheduler/events - 讀 cron_events.jsonl 返回最近 N 個
- GET /admin/retrospective/reports - 列 self-retrospective reports
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from app.core.rate_limiter import limiter
from app.extended.models import User
from app.core.dependencies import require_admin


router = APIRouter()


def _logs_dir() -> Path:
    """v6.13 對齊 L57 path SSOT"""
    return Path(os.getenv("CK_LOGS_DIR", "/app/logs"))


def _wiki_memory_dir() -> Path:
    """wiki/memory/ dir"""
    project_root = Path(os.getenv("CK_PROJECT_ROOT", "/app"))
    return project_root / "wiki" / "memory"


@router.get("/admin/scheduler/events", summary="Cron events 歷史 (jsonl 讀取)")
@limiter.limit("60/minute")
async def get_scheduler_events(
    request: Request,
    response: Response,  # slowapi headers_enabled 需此參數注入 rate-limit headers
    limit: int = Query(100, ge=1, le=1000),
    job_id: Optional[str] = Query(None, description="篩選特定 job"),
    status: Optional[str] = Query(None, description="success/failure"),
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """取得 cron 執行歷史 (從 cron_events.jsonl 讀)

    支援 limit / job_id / status 篩選
    """
    events_log = _logs_dir() / "cron_events.jsonl"
    if not events_log.exists():
        return {"events": [], "total": 0, "file": str(events_log)}

    try:
        lines = events_log.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        raise HTTPException(500, f"event log 讀取失敗: {e}")

    events = []
    for line in lines:
        try:
            ev = json.loads(line)
            if job_id and ev.get("job_id") != job_id:
                continue
            if status and ev.get("status") != status:
                continue
            events.append(ev)
        except json.JSONDecodeError:
            continue

    # 返回最近 N 個 (從末尾)
    return {
        "events": events[-limit:][::-1],  # 反序最新在前
        "total": len(events),
        "file": str(events_log),
        "filter": {"job_id": job_id, "status": status, "limit": limit},
    }


@router.get("/admin/scheduler/events/stats", summary="Cron events 統計摘要")
@limiter.limit("60/minute")
async def get_scheduler_events_stats(
    request: Request,
    response: Response,  # slowapi headers_enabled 需此參數注入 rate-limit headers
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """Cron events 統計（依 job_id 分組 + 成功失敗率）"""
    events_log = _logs_dir() / "cron_events.jsonl"
    if not events_log.exists():
        return {"jobs": [], "total_events": 0}

    try:
        lines = events_log.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        raise HTTPException(500, f"event log 讀取失敗: {e}")

    stats: Dict[str, Dict[str, Any]] = {}
    for line in lines:
        try:
            ev = json.loads(line)
            job = ev.get("job_id", "unknown")
            if job not in stats:
                stats[job] = {
                    "success": 0,
                    "failure": 0,
                    "total_duration_ms": 0,
                    "last_event": None,
                }
            if ev.get("status") == "success":
                stats[job]["success"] += 1
            elif ev.get("status") == "failure":
                stats[job]["failure"] += 1
            stats[job]["total_duration_ms"] += ev.get("duration_ms", 0) or 0
            stats[job]["last_event"] = ev
        except json.JSONDecodeError:
            continue

    # 轉 list + 加 derived
    result = []
    for job, s in stats.items():
        total = s["success"] + s["failure"]
        avg_ms = (s["total_duration_ms"] / total) if total else 0
        success_rate = (s["success"] / total * 100) if total else 0
        result.append({
            "job_id": job,
            "success_count": s["success"],
            "failure_count": s["failure"],
            "total_count": total,
            "success_rate_pct": round(success_rate, 1),
            "avg_duration_ms": round(avg_ms, 1),
            "last_event": s["last_event"],
        })
    result.sort(key=lambda x: x["total_count"], reverse=True)

    return {
        "jobs": result,
        "total_events": sum(j["total_count"] for j in result),
        "total_jobs": len(result),
    }


@router.get("/admin/retrospective/reports", summary="Daily Self-Retrospective 報告列表")
@limiter.limit("60/minute")
async def list_retrospective_reports(
    request: Request,
    response: Response,  # slowapi headers_enabled 需此參數注入 rate-limit headers
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """列出 wiki/memory/self-retrospective-reports/*.md"""
    reports_dir = _wiki_memory_dir() / "self-retrospective-reports"
    if not reports_dir.is_dir():
        return {"reports": [], "total": 0, "dir": str(reports_dir)}

    reports = []
    for f in sorted(reports_dir.glob("*.md"), reverse=True)[:limit]:
        try:
            stat = f.stat()
            text = f.read_text(encoding="utf-8", errors="ignore")[:3000]
            # 抓 Overall 狀態
            overall = "UNKNOWN"
            for line in text.splitlines()[:20]:
                if "**Overall**" in line:
                    overall = line.split(":")[-1].strip().rstrip("*").strip()
                    break
            reports.append({
                "date": f.stem,
                "filename": f.name,
                "size_bytes": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "overall": overall,
                "summary": text[:500],
            })
        except Exception:
            continue
    return {"reports": reports, "total": len(reports), "dir": str(reports_dir)}


@router.get("/admin/retrospective/reports/{date}", summary="特定日期 retrospective 完整內容")
@limiter.limit("60/minute")
async def get_retrospective_report(
    request: Request,
    response: Response,  # slowapi headers_enabled 需此參數注入 rate-limit headers
    date: str,
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """讀特定日期完整 markdown + json"""
    reports_dir = _wiki_memory_dir() / "self-retrospective-reports"
    md_file = reports_dir / f"{date}.md"
    json_file = reports_dir / f"{date}.json"

    if not md_file.exists():
        raise HTTPException(404, f"報告不存在: {date}")

    result = {
        "date": date,
        "markdown": md_file.read_text(encoding="utf-8", errors="ignore"),
    }
    if json_file.exists():
        try:
            result["json"] = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return result
