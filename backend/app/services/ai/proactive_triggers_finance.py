"""
Proactive Triggers — Finance 觸發掃描 (預算/發票/收據)

拆分自 proactive_triggers_erp.py，負責預算超支、待核銷發票等財務通知。

Version: 1.0.0
"""
import logging
from datetime import date, timedelta
from typing import List

from sqlalchemy import case as sa_case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.proactive_triggers import TriggerAlert

logger = logging.getLogger(__name__)


async def check_budget_overrun(
    db: AsyncSession,
    threshold_pct: float = 80,
) -> List[TriggerAlert]:
    """預算超支掃描 — 檢查各專案支出是否超過收入的閾值百分比"""
    try:
        from app.extended.models.finance import FinanceLedger
    except ImportError:
        return []

    alerts: List[TriggerAlert] = []

    stmt = (
        select(
            FinanceLedger.case_code,
            func.sum(
                sa_case(
                    (FinanceLedger.entry_type == "income", FinanceLedger.amount),
                    else_=0,
                )
            ).label("total_income"),
            func.sum(
                sa_case(
                    (FinanceLedger.entry_type == "expense", FinanceLedger.amount),
                    else_=0,
                )
            ).label("total_expense"),
        )
        .where(FinanceLedger.case_code.isnot(None))
        .group_by(FinanceLedger.case_code)
    )
    result = await db.execute(stmt)

    for row in result.all():
        income = float(row.total_income or 0)
        expense = float(row.total_expense or 0)
        if income <= 0:
            continue

        usage_pct = (expense / income) * 100
        if usage_pct >= threshold_pct:
            level = "critical" if usage_pct >= 100 else "warning"
            alerts.append(TriggerAlert(
                alert_type="budget_overrun",
                severity=level,
                title=f"專案預算使用率 {usage_pct:.0f}%",
                message=(
                    f"案件「{row.case_code}」支出 {expense:,.0f} 元 / "
                    f"收入 {income:,.0f} 元，使用率 {usage_pct:.1f}%"
                ),
                entity_type="finance",
                metadata={
                    "case_code": row.case_code,
                    "income": income,
                    "expense": expense,
                    "usage_pct": round(usage_pct, 1),
                },
            ))

    return alerts


async def check_pending_receipts(
    db: AsyncSession,
    stale_days: int = 7,
) -> List[TriggerAlert]:
    """待核銷發票提醒 — 財政部同步的發票超過 N 天仍未上傳收據"""
    try:
        from app.extended.models.invoice import ExpenseInvoice
    except ImportError:
        return []

    today = date.today()
    stale_threshold = today - timedelta(days=stale_days)
    alerts: List[TriggerAlert] = []

    result = await db.execute(
        select(func.count(ExpenseInvoice.id))
        .where(
            ExpenseInvoice.status == "pending_receipt",
            ExpenseInvoice.synced_at.isnot(None),
            ExpenseInvoice.synced_at < stale_threshold,
        )
    )
    stale_count = result.scalar() or 0

    if stale_count > 0:
        alerts.append(TriggerAlert(
            alert_type="pending_receipt_stale",
            severity="warning" if stale_count >= 5 else "info",
            title=f"{stale_count} 張發票待核銷超過 {stale_days} 天",
            message=(
                f"有 {stale_count} 張由財政部同步的發票已超過 {stale_days} 天"
                f"仍未上傳收據，請提醒相關人員完成核銷"
            ),
            entity_type="finance",
            metadata={
                "stale_count": stale_count,
                "stale_days": stale_days,
            },
        ))

    return alerts
