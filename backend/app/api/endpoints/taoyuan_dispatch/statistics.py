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
from app.core.dependencies import require_auth
from app.extended.models import User
from app.services.taoyuan import TaoyuanStatisticsService
from app.services.ai.domain.dispatch_progress_synthesizer import DispatchProgressSynthesizer
from app.schemas.taoyuan.statistics import (  # 2026-07-20 SSOT
    MorningStatusRequest,
    ProgressReportRequest,
)

router = APIRouter()


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
    生成派工進度彙整報告（結構化進度分類）

    回傳結構化報告：已完成/進行中/逾期分類 + 負責人統計 + 關鍵提醒
    """
    synthesizer = DispatchProgressSynthesizer(db)
    report = await synthesizer.generate_report(
        year=params.year,
        contract_project_id=params.contract_project_id,
    )
    return synthesizer.to_dict(report)


@router.post("/dispatch/morning-status", summary="晨報追蹤 — 派工狀態")
async def dispatch_morning_status(
    params: MorningStatusRequest = MorningStatusRequest(),
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
    from app.services.ai.domain.morning_report_service import _now_taipei

    today = _now_taipei().date()

    # 派工總覽：不以 d.deadline 欄位過濾（2026-06-16 owner 報「158 對應日期已填卻仍闕漏紀錄」）。
    #   deadline 欄位只是顯示字串；真實 closure_level 由 work_records / doc_links / upcoming_events
    #   決定（work_record.deadline_date 即排程依據，不需 d.deadline 欄位）。原 `WHERE deadline IS
    #   NOT NULL` 會誤排除「欄位空但有對應/排程」的派工 → 改為讓全部派工走相同 closure 計算。
    #   scope 僅本端點（不動共用 _ACTIVE_DISPATCHES_SQL，晨報生成不受影響）。
    sql = svc._ACTIVE_DISPATCHES_SQL.replace(
        "WHERE d.deadline IS NOT NULL\n          AND d.deadline != ''",
        "WHERE 1=1",
    )
    bind_params: dict = {}
    if params.contract_project_id:
        sql += "\n          AND d.contract_project_id = :cpid"
        bind_params["cpid"] = params.contract_project_id
    r = await db.execute(text(sql), bind_params)

    # 取 work_type_items 一次查詢
    wt_rows = await db.execute(text("""
        SELECT dwt.dispatch_order_id,
               STRING_AGG(dwt.work_type, ',' ORDER BY dwt.sort_order) AS types
        FROM taoyuan_dispatch_work_types dwt
        GROUP BY dwt.dispatch_order_id
    """))
    work_types_map: dict = {row[0]: row[1] for row in wt_rows.all()}

    # per-type 進度 — work_records 按 work_type_id 分組聚合
    pt_rows = await db.execute(text("""
        SELECT wr.dispatch_order_id, dwt.id AS wt_id, dwt.work_type, dwt.deadline,
               COUNT(wr.id) AS total,
               COUNT(wr.id) FILTER (WHERE wr.status = 'completed') AS completed
        FROM taoyuan_work_records wr
        JOIN taoyuan_dispatch_work_types dwt ON dwt.id = wr.work_type_id
        GROUP BY wr.dispatch_order_id, dwt.id, dwt.work_type, dwt.deadline
        ORDER BY dwt.sort_order
    """))
    per_type_map: dict[int, list] = {}
    for row in pt_rows.all():
        did = row[0]
        per_type_map.setdefault(did, []).append({
            "work_type_id": row[1],
            "work_type": row[2],
            "deadline": str(row[3]) if row[3] else None,
            "total": row[4],
            "completed": row[5],
        })

    # 作業類別 label 對照
    cat_labels = {
        "admin_notice": "行政通知", "dispatch_notice": "派工通知",
        "work_result": "成果回函", "meeting_notice": "會議通知",
        "meeting_record": "會議紀錄", "survey_notice": "會勘通知",
        "survey_record": "會勘紀錄", "other": "其他",
    }

    items = []
    for row in r.all():
        dl = svc._parse_roc_date(row[2])
        completed_n, total_n = row[12], row[13]
        next_event = row[14]
        closure = row[11]
        display_cat = row[15] or row[7] or ""  # bottleneck fallback latest

        # display_status: 4 大類精簡呈現（v5.8.0 最終版）
        # - 已完成/交付：closed / delivered / all_completed / pending_closure
        # - 排程中：有律定 + 交付期限 > 7 天
        # - 預警案件：交付期限 ≤ 7 天（含已逾期）
        # - 闕漏紀錄：無律定 或 0 紀錄（缺少必要資料）
        if closure in ("closed", "delivered", "all_completed", "pending_closure"):
            display_status = "已完成/交付"
        elif closure == "scheduled":
            display_status = "排程中"
        elif total_n == 0:
            display_status = "闕漏紀錄"
        elif dl and dl < today:
            display_status = "預警案件"
        elif closure == "warning":
            display_status = "預警案件"
        elif closure in ("needs_action", "active"):
            display_status = "闕漏紀錄"
        else:
            display_status = "闕漏紀錄"  # fallback

        dispatch_id = row[0]
        wt_str = work_types_map.get(dispatch_id, "")
        items.append({
            "id": dispatch_id,
            "dispatch_no": row[1],
            "deadline": str(dl) if dl else "",
            "deadline_raw": row[2],
            "project_name": row[3] or "",
            "handler": row[4] or "",
            "sub_case": row[5] or "",
            "survey_unit": row[17] or "",
            "closure_level": closure,
            "display_status": display_status,
            "work_category": display_cat,
            "work_category_label": cat_labels.get(display_cat, display_cat or "-"),
            "work_types": [t.strip() for t in wt_str.split(",") if t.strip()] if wt_str else [],
            "per_type_progress": per_type_map.get(dispatch_id, []),
            "completed_count": completed_n,
            "total_records": total_n,
            "progress": svc._format_dispatch_progress(
                row[6], row[7], row[8], row[9], row[10]
            ),
            "next_event": str(next_event.date()) if hasattr(next_event, 'date') and next_event else str(next_event) if next_event else None,
        })

    # 統計摘要 — 以 display_status 計
    status_counts = {}
    for item in items:
        ds = item["display_status"]
        status_counts[ds] = status_counts.get(ds, 0) + 1

    return JSONResponse(
        {
            "success": True,
            "total": len(items),
            "summary": status_counts,
            "items": items,
        },
        media_type="application/json; charset=utf-8",
    )
