"""
Proactive Triggers — PM 里程碑觸發掃描

拆分自 proactive_triggers_erp.py，負責 PM 里程碑逾期/到期通知。

Version: 1.0.0
"""
import logging
from datetime import date, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.proactive_triggers import TriggerAlert

logger = logging.getLogger(__name__)


async def check_pm_milestone_deadlines(
    db: AsyncSession,
    days_ahead: int = 7,
) -> List[TriggerAlert]:
    """檢查 PM 里程碑逾期與即將到期"""
    try:
        from app.extended.models.pm import PMMilestone, PMCase
    except ImportError:
        return []

    today = date.today()
    deadline_threshold = today + timedelta(days=days_ahead)
    alerts: List[TriggerAlert] = []

    # 已逾期里程碑
    overdue_result = await db.execute(
        select(
            PMMilestone.id,
            PMMilestone.milestone_name,
            PMMilestone.planned_date,
            PMMilestone.pm_case_id,
            PMCase.case_code,
            PMCase.case_name,
        )
        .join(PMCase, PMMilestone.pm_case_id == PMCase.id)
        .where(
            PMMilestone.planned_date < today,
            PMMilestone.planned_date.isnot(None),
            PMMilestone.status.notin_(["completed", "skipped"]),
            PMCase.status.in_(["planning", "in_progress"]),
        )
        .order_by(PMMilestone.planned_date)
        .limit(20)
    )
    for row in overdue_result.all():
        days_over = (today - row.planned_date).days
        alerts.append(TriggerAlert(
            alert_type="deadline_overdue",
            severity="critical" if days_over > 14 else "warning",
            title=f"PM 里程碑已逾期 {days_over} 天",
            message=(
                f"案件「{row.case_name}」({row.case_code}) 的里程碑"
                f"「{row.milestone_name}」已逾期 {days_over} 天"
            ),
            entity_type="pm_milestone",
            entity_id=row.pm_case_id,
            metadata={
                "milestone_id": row.id,
                "days_overdue": days_over,
                "case_code": row.case_code,
                "deadline": str(row.planned_date),
            },
        ))

    # 即將到期里程碑
    upcoming_result = await db.execute(
        select(
            PMMilestone.id,
            PMMilestone.milestone_name,
            PMMilestone.planned_date,
            PMMilestone.pm_case_id,
            PMCase.case_code,
            PMCase.case_name,
        )
        .join(PMCase, PMMilestone.pm_case_id == PMCase.id)
        .where(
            PMMilestone.planned_date >= today,
            PMMilestone.planned_date <= deadline_threshold,
            PMMilestone.planned_date.isnot(None),
            PMMilestone.status.notin_(["completed", "skipped"]),
            PMCase.status.in_(["planning", "in_progress"]),
        )
        .order_by(PMMilestone.planned_date)
        .limit(20)
    )
    for row in upcoming_result.all():
        days_left = (row.planned_date - today).days
        alerts.append(TriggerAlert(
            alert_type="deadline_warning",
            severity="warning" if days_left <= 3 else "info",
            title=f"PM 里程碑將於 {days_left} 天內到期",
            message=(
                f"案件「{row.case_name}」({row.case_code}) 的里程碑"
                f"「{row.milestone_name}」將於 {row.planned_date} 到期"
            ),
            entity_type="pm_milestone",
            entity_id=row.pm_case_id,
            metadata={
                "milestone_id": row.id,
                "days_remaining": days_left,
                "case_code": row.case_code,
                "deadline": str(row.planned_date),
            },
        ))

    return alerts
