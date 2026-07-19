"""Scheduler events & retrospective reports endpoints (v6.13, 2026-05-31)

Owner: 前端需提供專案排程紀錄追溯表 + 覆盤紀錄

提供端點（薄委派層）：
- GET /admin/scheduler/events        - cron 執行歷史
- GET /admin/scheduler/events/stats  - 依 job 分組統計
- GET /admin/retrospective/reports   - 覆盤報告列表
- GET /admin/retrospective/reports/{date} - 特定日期完整內容

2026-07-20 標準化：讀 jsonl/md + 聚合邏輯抽至 SchedulerEventsService（DDD），
端點只負責 HTTP 處理（參數/認證/錯誤碼），不再端點內直讀檔+聚合。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.core.rate_limiter import limiter
from app.extended.models import User
from app.core.dependencies import require_admin
from app.services.system.scheduler_events_service import SchedulerEventsService


router = APIRouter()


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
    """取得 cron 執行歷史 (從 cron_events.jsonl 讀)，支援 limit / job_id / status 篩選。"""
    try:
        return SchedulerEventsService().get_events(limit=limit, job_id=job_id, status=status)
    except Exception as e:
        raise HTTPException(500, f"event log 讀取失敗: {e}")


@router.get("/admin/scheduler/events/stats", summary="Cron events 統計摘要")
@limiter.limit("60/minute")
async def get_scheduler_events_stats(
    request: Request,
    response: Response,  # slowapi headers_enabled 需此參數注入 rate-limit headers
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """Cron events 統計（依 job_id 分組 + 成功失敗率）。"""
    try:
        return SchedulerEventsService().get_events_stats()
    except Exception as e:
        raise HTTPException(500, f"event log 讀取失敗: {e}")


@router.get("/admin/retrospective/reports", summary="Daily Self-Retrospective 報告列表")
@limiter.limit("60/minute")
async def list_retrospective_reports(
    request: Request,
    response: Response,  # slowapi headers_enabled 需此參數注入 rate-limit headers
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """列出 wiki/memory/self-retrospective-reports/*.md。"""
    return SchedulerEventsService().list_reports(limit=limit)


@router.get("/admin/retrospective/reports/{date}", summary="特定日期 retrospective 完整內容")
@limiter.limit("60/minute")
async def get_retrospective_report(
    request: Request,
    response: Response,  # slowapi headers_enabled 需此參數注入 rate-limit headers
    date: str,
    current_user: User = Depends(require_admin()),
) -> Dict[str, Any]:
    """讀特定日期完整 markdown + json。"""
    result = SchedulerEventsService().get_report(date)
    if result is None:
        raise HTTPException(404, f"報告不存在: {date}")
    return result
