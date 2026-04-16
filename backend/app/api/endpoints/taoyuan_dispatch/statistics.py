"""
桃園派工管理 - 統計 API

@version 2.0.0 - 重構使用 Service Layer
@date 2026-01-28
"""
from .common import (
    APIRouter,
    Depends,
    AsyncSession,
    get_async_db,
    TaoyuanStatisticsResponse,
    ProjectStatistics,
    DispatchStatistics,
    PaymentStatistics,
)
from typing import Optional
from pydantic import BaseModel, Field

from app.core.dependencies import require_auth
from app.extended.models import User
from app.services.taoyuan import TaoyuanStatisticsService
from app.services.ai.domain.dispatch_progress_synthesizer import DispatchProgressSynthesizer

router = APIRouter()


class ProgressReportRequest(BaseModel):
    """進度彙整請求"""
    year: Optional[int] = Field(None, description="民國年度（如 115），預設當前年度")
    contract_project_id: Optional[int] = Field(None, description="限定特定承攬案件")


def get_statistics_service(db: AsyncSession = Depends(get_async_db)) -> TaoyuanStatisticsService:
    """依賴注入：取得 TaoyuanStatisticsService"""
    return TaoyuanStatisticsService(db)


@router.post("/statistics", response_model=TaoyuanStatisticsResponse, summary="桃園查估派工統計資料")
async def get_statistics(
    contract_project_id: int,
    service: TaoyuanStatisticsService = Depends(get_statistics_service),
    current_user: User = Depends(require_auth()),
):
    """
    取得桃園查估派工統計資料

    包含：
    - 工程統計：總數、已派工、已完成、完成率
    - 派工統計：總數、有機關函文、有乾坤函文、作業類別數
    - 契金統計：本次派工金額、累進金額、剩餘金額、紀錄數
    """
    overview = await service.get_overview_statistics(contract_project_id)

    # 從 overview 取得統計資料
    dispatch_stats = overview.get('dispatch', {})
    project_stats = overview.get('project', {})
    payment_stats = overview.get('payment', {})

    return TaoyuanStatisticsResponse(
        success=True,
        projects=ProjectStatistics(
            total_count=project_stats.get('total', 0),
            dispatched_count=project_stats.get('dispatched', 0),
            completed_count=project_stats.get('completed', 0),
            completion_rate=project_stats.get('completion_rate', 0),
        ),
        dispatches=DispatchStatistics(
            total_count=dispatch_stats.get('total', 0),
            with_agency_doc_count=dispatch_stats.get('with_agency_doc', 0),
            with_company_doc_count=dispatch_stats.get('with_company_doc', 0),
            work_type_count=dispatch_stats.get('work_type_count', 0),
        ),
        payments=PaymentStatistics(
            total_current_amount=payment_stats.get('total_current', 0),
            total_cumulative_amount=payment_stats.get('total_cumulative', 0),
            total_remaining_amount=payment_stats.get('total_remaining', 0),
            payment_count=payment_stats.get('count', 0),
        ),
    )


@router.post("/progress-report", summary="派工進度彙整報告")
async def dispatch_progress_report(
    params: ProgressReportRequest = ProgressReportRequest(),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """
    生成派工進度彙整報告（對標 OpenClaw 進度彙整格式）

    回傳結構化報告：已完成/進行中/逾期分類 + 負責人統計 + 關鍵提醒
    """
    synthesizer = DispatchProgressSynthesizer(db)
    report = await synthesizer.generate_report(
        year=params.year,
        contract_project_id=params.contract_project_id,
    )
    return synthesizer.to_dict(report)


@router.post("/dispatch/morning-status", summary="晨報追蹤 — 全量派工狀態")
async def dispatch_morning_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_auth()),
):
    """回傳所有派工單的晨報 closure_level + 進度。

    前端用於「晨報追蹤」Tab，呈現分層狀態：
    delivered / all_completed / scheduled / active / pending_closure / closed / no_record
    """
    from fastapi.responses import JSONResponse
    from app.services.ai.domain.morning_report_service import MorningReportService

    svc = MorningReportService(db)
    from sqlalchemy import text
    r = await db.execute(text(svc._ACTIVE_DISPATCHES_SQL))
    items = []
    for row in r.all():
        dl = svc._parse_roc_date(row[2])
        completed_n, total_n = row[12], row[13]
        next_event = row[14]
        items.append({
            "id": row[0],
            "dispatch_no": row[1],
            "deadline": str(dl) if dl else row[2],
            "deadline_raw": row[2],
            "project_name": row[3] or "",
            "handler": row[4] or "",
            "sub_case": row[5] or "",
            "closure_level": row[11],
            "completed_count": completed_n,
            "total_records": total_n,
            "progress": svc._format_dispatch_progress(
                row[6], row[7], row[8], row[9], row[10]
            ),
            "next_event": str(next_event.date()) if hasattr(next_event, 'date') and next_event else str(next_event) if next_event else None,
        })

    # 統計摘要
    levels = {}
    for item in items:
        lv = item["closure_level"]
        levels[lv] = levels.get(lv, 0) + 1

    return JSONResponse(
        {
            "success": True,
            "total": len(items),
            "summary": levels,
            "items": items,
        },
        media_type="application/json; charset=utf-8",
    )
