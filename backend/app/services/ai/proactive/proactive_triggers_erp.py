"""
Proactive Triggers — PM/ERP 觸發掃描器 (Facade)

編排所有 PM/ERP 觸發規則，委派至子模組：
- proactive_triggers_pm.py: PM 里程碑逾期/到期
- proactive_triggers_finance.py: 預算超支/待核銷收據

本檔案保留 ERP 請款/發票/廠商付款的觸發邏輯。

Version: 2.0.0 — refactored from 534L monolith
"""
import logging
from datetime import date, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.proactive.proactive_triggers import TriggerAlert

logger = logging.getLogger(__name__)


class ERPTriggerScanner:
    """PM/ERP 主動觸發掃描器 (Facade)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan_all(
        self,
        deadline_days: int = 7,
    ) -> List[TriggerAlert]:
        """掃描所有 PM/ERP 觸發條件"""
        alerts: List[TriggerAlert] = []

        # PM 里程碑 (委派)
        from app.services.ai.proactive.proactive_triggers_pm import check_pm_milestone_deadlines
        alerts.extend(await check_pm_milestone_deadlines(self.db, deadline_days))

        # ERP 請款/發票 (本地)
        alerts.extend(await self.check_erp_overdue_billings())
        alerts.extend(await self.check_invoice_reminder())
        alerts.extend(await self.check_vendor_payment_milestones())
        alerts.extend(await self.check_amount_mismatch())

        # 預算/收據 (委派)
        from app.services.ai.proactive.proactive_triggers_finance import (
            check_budget_overrun, check_pending_receipts,
        )
        alerts.extend(await check_budget_overrun(self.db))
        alerts.extend(await check_pending_receipts(self.db))

        return alerts

    async def check_pm_milestone_deadlines(
        self, days_ahead: int = 7,
    ) -> List[TriggerAlert]:
        """委派至 proactive_triggers_pm"""
        from app.services.ai.proactive.proactive_triggers_pm import check_pm_milestone_deadlines
        return await check_pm_milestone_deadlines(self.db, days_ahead)

    async def check_erp_overdue_billings(self) -> List[TriggerAlert]:
        """檢查 ERP 逾期未收款請款單"""
        try:
            from app.extended.models.erp import ERPBilling, ERPQuotation
        except ImportError:
            return []

        today = date.today()
        alerts: List[TriggerAlert] = []

        # 逾期未收
        overdue_result = await self.db.execute(
            select(
                ERPBilling.id,
                ERPBilling.billing_amount,
                ERPBilling.billing_date,
                ERPBilling.payment_status,
                ERPBilling.billing_period,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
            )
            .join(ERPQuotation, ERPBilling.erp_quotation_id == ERPQuotation.id)
            .where(
                ERPBilling.billing_date < today,
                ERPBilling.billing_date.isnot(None),
                ERPBilling.payment_status.in_(["pending", "partial"]),
            )
            .order_by(ERPBilling.billing_date)
            .limit(20)
        )
        for row in overdue_result.all():
            days_over = (today - row.billing_date).days
            amount_str = f"{float(row.billing_amount):,.0f}" if row.billing_amount else "未知"
            severity = "critical" if days_over > 30 else "warning"

            alerts.append(TriggerAlert(
                alert_type="billing_overdue",
                severity=severity,
                title=f"請款逾期 {days_over} 天 ({amount_str} 元)",
                message=(
                    f"案件「{row.case_name}」({row.case_code}) "
                    f"請款 {amount_str} 元已逾期 {days_over} 天"
                ),
                entity_type="erp_billing",
                entity_id=row.id,
                metadata={
                    "days_overdue": days_over,
                    "amount": str(row.billing_amount),
                    "case_code": row.case_code,
                    "billing_date": str(row.billing_date),
                },
            ))

        # 即將到期 (D-7)
        upcoming_threshold = today + timedelta(days=7)
        upcoming_result = await self.db.execute(
            select(
                ERPBilling.id,
                ERPBilling.billing_amount,
                ERPBilling.billing_date,
                ERPBilling.billing_period,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
            )
            .join(ERPQuotation, ERPBilling.erp_quotation_id == ERPQuotation.id)
            .where(
                ERPBilling.billing_date >= today,
                ERPBilling.billing_date <= upcoming_threshold,
                ERPBilling.billing_date.isnot(None),
                ERPBilling.payment_status.in_(["pending", "partial"]),
            )
            .order_by(ERPBilling.billing_date)
            .limit(20)
        )
        for row in upcoming_result.all():
            days_left = (row.billing_date - today).days
            amount_str = f"{float(row.billing_amount):,.0f}" if row.billing_amount else "未知"

            alerts.append(TriggerAlert(
                alert_type="billing_upcoming",
                severity="warning" if days_left <= 3 else "info",
                title=f"請款 {days_left} 天後到期 ({amount_str} 元)",
                message=(
                    f"案件「{row.case_name}」({row.case_code}) "
                    f"請款 {amount_str} 元將於 {row.billing_date} 到期"
                ),
                entity_type="erp_billing",
                entity_id=row.id,
                metadata={
                    "days_remaining": days_left,
                    "amount": str(row.billing_amount),
                    "case_code": row.case_code,
                },
            ))

        return alerts

    async def check_invoice_reminder(self) -> List[TriggerAlert]:
        """發票開立提醒 — 已請款但尚未開票"""
        try:
            from app.extended.models.erp import ERPBilling, ERPInvoice, ERPQuotation
        except ImportError:
            return []

        alerts: List[TriggerAlert] = []

        # 找到有請款但無發票的 quotation
        billed_ids = select(ERPBilling.erp_quotation_id).where(
            ERPBilling.payment_status.in_(["unpaid", "partial"])
        ).distinct()

        invoiced_ids = select(ERPInvoice.erp_quotation_id).distinct()

        result = await self.db.execute(
            select(
                ERPQuotation.id,
                ERPQuotation.case_code,
                ERPQuotation.case_name,
            )
            .where(
                ERPQuotation.id.in_(billed_ids),
                ~ERPQuotation.id.in_(invoiced_ids),
            )
            .limit(10)
        )

        for row in result.all():
            alerts.append(TriggerAlert(
                alert_type="invoice_missing",
                severity="info",
                title=f"案件待開票: {row.case_code}",
                message=(
                    f"案件「{row.case_name}」({row.case_code}) "
                    f"已有請款紀錄但尚未開立發票"
                ),
                entity_type="erp_quotation",
                entity_id=row.id,
                metadata={"case_code": row.case_code},
            ))

        return alerts

    async def check_vendor_payment_milestones(self) -> List[TriggerAlert]:
        """外包付款里程碑提醒 — 廠商應付帳款即將到期或已逾期"""
        try:
            from app.extended.models.erp import ERPVendorPayable, ERPQuotation
        except ImportError:
            return []

        today = date.today()
        alerts: List[TriggerAlert] = []

        # 已逾期未付
        overdue_result = await self.db.execute(
            select(
                ERPVendorPayable.id,
                ERPVendorPayable.vendor_name,
                ERPVendorPayable.payable_amount,
                ERPVendorPayable.due_date,
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

            alerts.append(TriggerAlert(
                alert_type="vendor_payment_overdue",
                severity="critical" if days_over > 14 else "warning",
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

        # 即將到期 (D-3)
        upcoming_threshold = today + timedelta(days=3)
        upcoming_result = await self.db.execute(
            select(
                ERPVendorPayable.id,
                ERPVendorPayable.vendor_name,
                ERPVendorPayable.payable_amount,
                ERPVendorPayable.due_date,
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

            alerts.append(TriggerAlert(
                alert_type="vendor_payment_warning",
                severity="warning" if days_left <= 1 else "info",
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

    async def check_amount_mismatch(self) -> List[TriggerAlert]:
        """
        財務異常偵測：報價↔請款↔應付金額不一致。

        規則:
        1. 請款總額 > 報價金額 (超支)
        2. 應付總額 > 報價金額 (超支)
        3. 請款總額 vs 應付總額差異 > 10% (不一致)
        """
        from app.extended.models.erp import ERPQuotation, ERPBilling, ERPVendorPayable
        from sqlalchemy import func as sqlfunc

        alerts: List[TriggerAlert] = []

        quotations = (await self.db.execute(
            select(ERPQuotation.id, ERPQuotation.case_code, ERPQuotation.case_name, ERPQuotation.total_price)
            .where(ERPQuotation.deleted_at.is_(None))
            .where(ERPQuotation.total_price > 0)
        )).all()

        for q_id, case_code, case_name, total_price in quotations:
            q_amount = float(total_price)

            billing_total = float((await self.db.execute(
                select(sqlfunc.coalesce(sqlfunc.sum(ERPBilling.billing_amount), 0))
                .where(ERPBilling.erp_quotation_id == q_id)
            )).scalar() or 0)

            payable_total = float((await self.db.execute(
                select(sqlfunc.coalesce(sqlfunc.sum(ERPVendorPayable.payable_amount), 0))
                .where(ERPVendorPayable.erp_quotation_id == q_id)
            )).scalar() or 0)

            if billing_total > q_amount * 1.01:
                alerts.append(TriggerAlert(
                    alert_type="billing_exceeds_quotation", severity="critical",
                    title=f"請款超支 {billing_total - q_amount:,.0f} 元",
                    message=f"案件「{case_name}」({case_code}) 請款 {billing_total:,.0f} > 報價 {q_amount:,.0f}",
                    entity_type="erp_quotation", entity_id=q_id,
                    metadata={"case_code": case_code, "quotation": q_amount, "billed": billing_total},
                ))

            if payable_total > q_amount * 1.01:
                alerts.append(TriggerAlert(
                    alert_type="payable_exceeds_quotation", severity="warning",
                    title=f"應付超支 {payable_total - q_amount:,.0f} 元",
                    message=f"案件「{case_name}」({case_code}) 應付 {payable_total:,.0f} > 報價 {q_amount:,.0f}",
                    entity_type="erp_quotation", entity_id=q_id,
                    metadata={"case_code": case_code, "quotation": q_amount, "payable": payable_total},
                ))

            if billing_total > 0 and payable_total > 0:
                diff_pct = abs(billing_total - payable_total) / max(billing_total, payable_total) * 100
                if diff_pct > 10:
                    alerts.append(TriggerAlert(
                        alert_type="billing_payable_mismatch", severity="warning",
                        title=f"請款/應付差異 {diff_pct:.1f}%",
                        message=f"案件「{case_name}」請款 {billing_total:,.0f} vs 應付 {payable_total:,.0f}",
                        entity_type="erp_quotation", entity_id=q_id,
                        metadata={"case_code": case_code, "billed": billing_total, "payable": payable_total},
                    ))

        return alerts
