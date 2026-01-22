"""
桃園派工管理 - 統計 API

@version 1.0.0
@date 2026-01-22
"""
from .common import (
    APIRouter,
    Depends,
    AsyncSession,
    select,
    get_async_db,
    TaoyuanProject,
    TaoyuanDispatchOrder,
    TaoyuanContractPayment,
    TaoyuanStatisticsResponse,
    ProjectStatistics,
    DispatchStatistics,
    PaymentStatistics,
)

router = APIRouter()


@router.post("/statistics", response_model=TaoyuanStatisticsResponse, summary="桃園查估派工統計資料")
async def get_statistics(
    contract_project_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    取得桃園查估派工統計資料

    包含：
    - 工程統計：總數、已派工、已完成、完成率
    - 派工統計：總數、有機關函文、有乾坤函文、作業類別數
    - 契金統計：本次派工金額、累進金額、剩餘金額、紀錄數
    """
    # 查詢工程統計
    project_query = select(TaoyuanProject).filter(
        TaoyuanProject.contract_project_id == contract_project_id
    )
    project_result = await db.execute(project_query)
    projects = project_result.scalars().all()

    total_projects = len(projects)
    dispatched_count = sum(1 for p in projects if p.land_agreement_status or p.building_survey_status)
    completed_count = sum(1 for p in projects if p.acceptance_status == '已驗收')
    completion_rate = round((completed_count / total_projects * 100) if total_projects > 0 else 0, 1)

    # 查詢派工統計
    dispatch_query = select(TaoyuanDispatchOrder).filter(
        TaoyuanDispatchOrder.contract_project_id == contract_project_id
    )
    dispatch_result = await db.execute(dispatch_query)
    dispatches = dispatch_result.scalars().all()

    total_dispatches = len(dispatches)
    with_agency_doc = sum(1 for d in dispatches if d.agency_doc_id is not None)
    with_company_doc = sum(1 for d in dispatches if d.company_doc_id is not None)
    work_types = set(d.work_type for d in dispatches if d.work_type)
    work_type_count = len(work_types)

    # 查詢契金統計
    # 先取得該專案所有派工單 ID
    dispatch_ids = [d.id for d in dispatches]

    if dispatch_ids:
        payment_query = select(TaoyuanContractPayment).filter(
            TaoyuanContractPayment.dispatch_order_id.in_(dispatch_ids)
        )
        payment_result = await db.execute(payment_query)
        payments = payment_result.scalars().all()
    else:
        payments = []

    total_current = sum(float(p.current_amount or 0) for p in payments)
    total_cumulative = sum(float(p.cumulative_amount or 0) for p in payments)
    total_remaining = sum(float(p.remaining_amount or 0) for p in payments)
    payment_count = len(payments)

    return TaoyuanStatisticsResponse(
        success=True,
        projects=ProjectStatistics(
            total_count=total_projects,
            dispatched_count=dispatched_count,
            completed_count=completed_count,
            completion_rate=completion_rate,
        ),
        dispatches=DispatchStatistics(
            total_count=total_dispatches,
            with_agency_doc_count=with_agency_doc,
            with_company_doc_count=with_company_doc,
            work_type_count=work_type_count,
        ),
        payments=PaymentStatistics(
            total_current_amount=total_current,
            total_cumulative_amount=total_cumulative,
            total_remaining_amount=total_remaining,
            payment_count=payment_count,
        ),
    )
