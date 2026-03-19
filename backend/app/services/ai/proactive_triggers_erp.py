"""
Proactive Triggers — PM/ERP 觸發掃描器

從 proactive_triggers.py 拆分，負責 PM 里程碑與 ERP 請款/發票/廠商付款的主動通知。

Version: 1.0.0
Created: 2026-03-19
"""

import logging
from datetime import date, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.proactive_triggers import TriggerAlert

logger = logging.getLogger(__name__)


class ERPTriggerScanner:
    """
    PM/ERP 主動觸發掃描器

    Usage:
        scanner = ERPTriggerScanner(db)
        alerts = await scanner.scan_all()
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan_all(
        self,
        deadline_days: int = 7,
    ) -> List[TriggerAlert]:
        """掃描所有 PM/ERP 觸發條件"""
        alerts: List[TriggerAlert] = []

        pm_alerts = await self.check_pm_milestone_deadlines(deadline_days)
        alerts.extend(pm_alerts)

        erp_alerts = await self.check_erp_overdue_billings()
        alerts.extend(erp_alerts)

        invoice_alerts = await self.check_invoice_reminder()
        alerts.extend(invoice_alerts)

        vendor_alerts = await self.check_vendor_payment_milestones()
        alerts.extend(vendor_alerts)

        return alerts

    async def check_pm_milestone_deadlines(
        self,
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

        # 已逾期里程碑（planned_date 已過且狀態非 completed/skipped）
        overdue_result = await self.db.execute(
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
        upcoming_result = await self.db.execute(
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

    async def check_erp_overdue_billings(self) -> List[TriggerAlert]:
        """檢查 ERP 逾期未收款請款單（以 billing_date 為到期基準）"""
        try:
            from app.extended.models.erp import ERPBilling, ERPQuotation
        except ImportError:
            return []

        today = date.today()
        alerts: List[TriggerAlert] = []

        # 已逾期且未付清的請款單（billing_date 已過 30 天仍未付清）
        overdue_threshold = today - timedelta(days=30)
        overdue_result = await self.db.execute(
            select(
                ERPBilling.id,
                ERPBilling.billing_period,
                ERPBilling.billing_amount,
                ERPBilling.billing_date,
                ERPBilling.payment_status,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
            )
            .join(ERPQuotation, ERPBilling.erp_quotation_id == ERPQuotation.id)
            .where(
                ERPBilling.billing_date < overdue_threshold,
                ERPBilling.billing_date.isnot(None),
                ERPBilling.payment_status.in_(["pending", "partial"]),
            )
            .order_by(ERPBilling.billing_date)
            .limit(20)
        )
        for row in overdue_result.all():
            days_over = (today - row.billing_date).days
            amount_str = f"{float(row.billing_amount):,.0f}" if row.billing_amount else "未知"
            severity = "critical" if days_over > 60 else "warning"
            alerts.append(TriggerAlert(
                alert_type="payment_overdue",
                severity=severity,
                title=f"ERP 請款逾期 {days_over} 天 ({amount_str} 元)",
                message=(
                    f"案件「{row.case_name}」({row.case_code}) "
                    f"{row.billing_period or '?'} 請款 {amount_str} 元"
                    f"已逾期 {days_over} 天，狀態：{row.payment_status}"
                ),
                entity_type="erp_billing",
                entity_id=row.id,
                metadata={
                    "days_overdue": days_over,
                    "amount": str(row.billing_amount),
                    "case_code": row.case_code,
                    "billing_date": str(row.billing_date),
                    "payment_status": row.payment_status,
                },
            ))

        # 30 天內請款且仍未付清
        upcoming_result = await self.db.execute(
            select(
                ERPBilling.id,
                ERPBilling.billing_period,
                ERPBilling.billing_amount,
                ERPBilling.billing_date,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
            )
            .join(ERPQuotation, ERPBilling.erp_quotation_id == ERPQuotation.id)
            .where(
                ERPBilling.billing_date >= overdue_threshold,
                ERPBilling.billing_date <= today,
                ERPBilling.billing_date.isnot(None),
                ERPBilling.payment_status == "pending",
            )
            .order_by(ERPBilling.billing_date)
            .limit(20)
        )
        for row in upcoming_result.all():
            days_since = (today - row.billing_date).days
            amount_str = f"{float(row.billing_amount):,.0f}" if row.billing_amount else "未知"
            alerts.append(TriggerAlert(
                alert_type="payment_warning",
                severity="warning" if days_since >= 14 else "info",
                title=f"ERP 請款已 {days_since} 天未收款",
                message=(
                    f"案件「{row.case_name}」({row.case_code}) "
                    f"{row.billing_period or '?'} 請款 {amount_str} 元"
                    f"已請款 {days_since} 天尚未收款"
                ),
                entity_type="erp_billing",
                entity_id=row.id,
                metadata={
                    "days_since_billing": days_since,
                    "amount": str(row.billing_amount),
                    "case_code": row.case_code,
                    "billing_date": str(row.billing_date),
                },
            ))

        return alerts

    async def check_invoice_reminder(self) -> List[TriggerAlert]:
        """
        發票催開預警 — PM 案件已完工但 ERP 尚未開立發票。

        條件: PM status='completed' 且對應 case_code 在 ERP 中無任何 issued 發票。
        """
        try:
            from app.extended.models.pm import PMCase
            from app.extended.models.erp import ERPQuotation, ERPInvoice
        except ImportError:
            return []

        alerts: List[TriggerAlert] = []

        # 找到已完工的 PM 案件，其 case_code 有對應 ERP 報價但無已開立發票
        subq_has_invoice = (
            select(ERPQuotation.case_code)
            .join(ERPInvoice, ERPInvoice.erp_quotation_id == ERPQuotation.id)
            .where(ERPInvoice.status == "issued")
            .distinct()
            .correlate(ERPQuotation)
        )

        result = await self.db.execute(
            select(
                PMCase.id,
                PMCase.case_code,
                PMCase.case_name,
                PMCase.actual_end_date,
                PMCase.end_date,
            )
            .where(
                PMCase.status == "completed",
                PMCase.case_code.isnot(None),
                PMCase.case_code.notin_(subq_has_invoice),
            )
            .order_by(PMCase.updated_at.desc())
            .limit(20)
        )

        today = date.today()
        for row in result.all():
            end = row.actual_end_date or row.end_date
            days_since = (today - end).days if end else 0
            severity = "critical" if days_since > 30 else "warning"

            alerts.append(TriggerAlert(
                alert_type="invoice_reminder",
                severity=severity,
                title=f"案件完工 {days_since} 天未開發票",
                message=(
                    f"案件「{row.case_name}」({row.case_code}) "
                    f"已完工 {days_since} 天，尚未開立銷項發票"
                ),
                entity_type="pm_case",
                entity_id=row.id,
                metadata={
                    "case_code": row.case_code,
                    "days_since_completion": days_since,
                    "completion_date": str(end) if end else None,
                },
            ))

        return alerts

    async def check_vendor_payment_milestones(self) -> List[TriggerAlert]:
        """
        外包付款里程碑提醒 — 廠商應付帳款即將到期或已逾期。

        D-3: info 提醒
        D-1: warning 提醒
        已逾期: critical/warning 依天數
        """
        try:
            from app.extended.models.erp import ERPVendorPayable, ERPQuotation
        except ImportError:
            return []

        today = date.today()
        alerts: List[TriggerAlert] = []

        # 已逾期未付的廠商應付
        overdue_result = await self.db.execute(
            select(
                ERPVendorPayable.id,
                ERPVendorPayable.vendor_name,
                ERPVendorPayable.payable_amount,
                ERPVendorPayable.due_date,
                ERPVendorPayable.description,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
            )
            .join(ERPQuotation, ERPVendorPayable.erp_quotation_id == ERPQuotation.id)
            .where(
                ERPVendorPayable.due_date < today,
                ERPVendorPayable.due_date.isnot(None),
                ERPVendorPayable.payment_status.in_(["unpaid", "partial"]),
            )
            .order_by(ERPVendorPayable.due_date)
            .limit(20)
        )
        for row in overdue_result.all():
            days_over = (today - row.due_date).days
            amount_str = f"{float(row.payable_amount):,.0f}" if row.payable_amount else "未知"
            severity = "critical" if days_over > 14 else "warning"

            alerts.append(TriggerAlert(
                alert_type="vendor_payment_overdue",
                severity=severity,
                title=f"外包付款逾期 {days_over} 天 ({amount_str} 元)",
                message=(
                    f"案件「{row.case_name}」({row.case_code}) "
                    f"廠商「{row.vendor_name}」應付 {amount_str} 元"
                    f"已逾期 {days_over} 天"
                ),
                entity_type="erp_vendor_payable",
                entity_id=row.id,
                metadata={
                    "days_overdue": days_over,
                    "amount": str(row.payable_amount),
                    "vendor_name": row.vendor_name,
                    "case_code": row.case_code,
                    "due_date": str(row.due_date),
                },
            ))

        # 即將到期 (D-3 ~ D-1)
        upcoming_threshold = today + timedelta(days=3)
        upcoming_result = await self.db.execute(
            select(
                ERPVendorPayable.id,
                ERPVendorPayable.vendor_name,
                ERPVendorPayable.payable_amount,
                ERPVendorPayable.due_date,
                ERPVendorPayable.description,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
            )
            .join(ERPQuotation, ERPVendorPayable.erp_quotation_id == ERPQuotation.id)
            .where(
                ERPVendorPayable.due_date >= today,
                ERPVendorPayable.due_date <= upcoming_threshold,
                ERPVendorPayable.due_date.isnot(None),
                ERPVendorPayable.payment_status.in_(["unpaid", "partial"]),
            )
            .order_by(ERPVendorPayable.due_date)
            .limit(20)
        )
        for row in upcoming_result.all():
            days_left = (row.due_date - today).days
            amount_str = f"{float(row.payable_amount):,.0f}" if row.payable_amount else "未知"
            severity = "warning" if days_left <= 1 else "info"

            alerts.append(TriggerAlert(
                alert_type="vendor_payment_warning",
                severity=severity,
                title=f"外包付款 {days_left} 天內到期 ({amount_str} 元)",
                message=(
                    f"案件「{row.case_name}」({row.case_code}) "
                    f"廠商「{row.vendor_name}」應付 {amount_str} 元"
                    f"將於 {row.due_date} 到期"
                ),
                entity_type="erp_vendor_payable",
                entity_id=row.id,
                metadata={
                    "days_remaining": days_left,
                    "amount": str(row.payable_amount),
                    "vendor_name": row.vendor_name,
                    "case_code": row.case_code,
                    "due_date": str(row.due_date),
                },
            ))

        return alerts
