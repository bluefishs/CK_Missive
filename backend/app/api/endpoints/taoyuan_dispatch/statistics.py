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
from app.services.ai.dispatch_progress_synthesizer import DispatchProgressSynthesizer

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
