"""
費用報銷審核服務 — 多層審批 + 預算聯防 + 通知

拆分自 expense_invoice_service.py，處理審核工作流邏輯。

Version: 1.0.0
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from decimal import Decimal

from app.extended.models.invoice import ExpenseInvoice
from app.schemas.erp.expense import (
    APPROVAL_THRESHOLD, APPROVAL_TRANSITIONS,
    BUDGET_WARNING_PCT, BUDGET_BLOCK_PCT,
)
from app.repositories.erp.expense_invoice_repository import ExpenseInvoiceRepository
from app.services.finance_ledger_service import FinanceLedgerService
from app.services.audit_mixin import AuditableServiceMixin

import logging

logger = logging.getLogger(__name__)


class ExpenseApprovalService(AuditableServiceMixin):
    """費用報銷審核工作流"""

    AUDIT_TABLE = "expense_invoices"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExpenseInvoiceRepository(db)
        self.ledger_service = FinanceLedgerService(db)

    async def approve(self, invoice_id: int) -> Optional[ExpenseInvoice]:
        """多層審核推進 — 依金額門檻自動決定下一狀態

        ≤30K TWD: pending → manager_approved → verified (二級)
        >30K TWD: pending → manager_approved → finance_approved → verified (三級)
        僅 verified 狀態觸發帳本入帳。

        預算聯防：即將進入 verified 時檢查專案預算水位
        - >100%: 攔截審核 (需總經理介入)
        - >80%: 警告但放行 (附帶預警訊息)
        """
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None

        current = invoice.status
        if current in ("verified", "rejected"):
            raise ValueError(f"此發票狀態為「{current}」，不可進行審核操作")

        allowed = APPROVAL_TRANSITIONS.get(current, [])
        if "rejected" in allowed:
            allowed = [s for s in allowed if s != "rejected"]
        if not allowed:
            raise ValueError(f"狀態「{current}」無法進行審核推進")

        next_status = self._determine_next_approval(current, invoice.amount)

        if next_status not in APPROVAL_TRANSITIONS.get(current, []):
            raise ValueError(f"非法狀態流轉: {current} → {next_status}")

        # === 預算聯防控制 ===
        budget_warning: Optional[str] = None
        if next_status == "verified" and invoice.case_code:
            budget_warning = await self._check_budget(invoice.case_code, invoice.amount)

        await self.repo.update_status(invoice, next_status)

        # 僅最終 verified 才寫入帳本
        if next_status == "verified":
            await self.ledger_service.record_from_expense(invoice)

        await self.repo.commit()

        # 通知推送
        await self._notify_status_change(invoice, current, next_status, budget_warning)

        # 發布 expense.approved 領域事件 (僅 verified 最終通過時)
        if next_status == "verified":
            try:
                from app.core.event_bus import EventBus
                from app.core.domain_events import DomainEvent, EventType
                bus = EventBus.get_instance()
                await bus.publish(DomainEvent(
                    event_type=EventType.EXPENSE_APPROVED,
                    payload={
                        "expense_id": invoice.id,
                        "amount": float(invoice.amount or 0),
                        "case_code": invoice.case_code or "",
                        "approved_by": invoice.user_id,
                    },
                ))
            except Exception:
                pass

        # 將預算警告附加為動態屬性，API 層可讀取
        invoice._budget_warning = budget_warning  # type: ignore[attr-defined]
        await self.audit_update(invoice_id, {"status": next_status, "action": "approve"})
        return invoice

    async def reject(self, invoice_id: int, reason: Optional[str] = None) -> Optional[ExpenseInvoice]:
        """駁回報銷 — 任何非終態階段皆可駁回"""
        invoice = await self.repo.get_by_id(invoice_id)
        if not invoice:
            return None
        if invoice.status in ("verified", "rejected"):
            raise ValueError(f"此發票狀態為「{invoice.status}」，不可駁回")

        allowed = APPROVAL_TRANSITIONS.get(invoice.status, [])
        if "rejected" not in allowed:
            raise ValueError(f"狀態「{invoice.status}」不允許駁回")

        notes_append = f"[駁回] {reason}" if reason else None
        result = await self.repo.update_status(invoice, "rejected", notes_append=notes_append)
        if result:
            await self.audit_update(invoice_id, {"status": "rejected", "action": "reject", "reason": reason})
        return result

    def _determine_next_approval(self, current_status: str, amount: Decimal) -> str:
        """根據當前狀態與金額決定下一審核狀態"""
        amount_val = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
        is_high_value = amount_val > APPROVAL_THRESHOLD

        if current_status == "pending":
            return "manager_approved"
        elif current_status == "manager_approved":
            return "finance_approved" if is_high_value else "verified"
        elif current_status == "finance_approved":
            return "verified"
        return current_status

    async def _notify_status_change(
        self, invoice, old_status: str, new_status: str, budget_warning: Optional[str] = None
    ) -> None:
        """核銷狀態變更通知"""
        try:
            from app.services.notification_helpers import _safe_create_notification

            STATUS_LABELS = {
                "pending": "待主管審核", "manager_approved": "主管已核准",
                "finance_approved": "財務已核准", "verified": "最終通過",
                "rejected": "已駁回",
            }
            title = f"核銷審核: {invoice.inv_num} → {STATUS_LABELS.get(new_status, new_status)}"
            msg = f"發票 {invoice.inv_num} (NT$ {invoice.amount:,.0f}) 狀態: {STATUS_LABELS.get(old_status, old_status)} → {STATUS_LABELS.get(new_status, new_status)}"
            if budget_warning:
                msg += f"\n⚠️ {budget_warning}"

            severity = "info"
            if new_status == "verified":
                severity = "success"
            elif new_status == "rejected":
                severity = "warning"

            await _safe_create_notification(
                notification_type="expense_approval",
                severity=severity,
                title=title,
                message=msg,
                source_table="expense_invoices",
                source_id=invoice.id,
                user_id=invoice.user_id,
            )
        except Exception as e:
            logger.debug(f"通知推送失敗 (非阻塞): {e}")

    async def _check_budget(self, case_code: str, invoice_amount: Decimal) -> Optional[str]:
        """預算聯防 — 檢查專案預算水位"""
        from sqlalchemy import select
        from app.extended.models.erp import ERPQuotation

        stmt = (
            select(ERPQuotation.budget_limit)
            .where(ERPQuotation.case_code == case_code)
            .where(ERPQuotation.budget_limit.is_not(None))
            .order_by(ERPQuotation.budget_limit.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        budget_limit = result.scalar_one_or_none()

        if not budget_limit or budget_limit <= 0:
            return None

        budget = Decimal(str(budget_limit))
        amount = Decimal(str(invoice_amount)) if not isinstance(invoice_amount, Decimal) else invoice_amount

        balance = await self.ledger_service.get_case_balance(case_code)
        cumulative_expense = Decimal(str(balance.get("expense", 0)))

        projected = cumulative_expense + amount
        usage_pct = (projected / budget) * Decimal("100")

        logger.info(
            f"預算檢查 [{case_code}]: 累計支出={cumulative_expense}, "
            f"本筆={amount}, 預算={budget}, 預測使用率={usage_pct:.1f}%"
        )

        if usage_pct > BUDGET_BLOCK_PCT:
            raise ValueError(
                f"預算超限！專案 {case_code} 累計支出將達 {projected:,.0f} 元 "
                f"(預算 {budget:,.0f} 元，使用率 {usage_pct:.1f}%)。"
                f"請聯繫總經理核准後再行操作。"
            )

        if usage_pct > BUDGET_WARNING_PCT:
            return (
                f"⚠️ 預算警告：專案 {case_code} 核准後累計支出將達 {projected:,.0f} 元 "
                f"(預算 {budget:,.0f} 元，使用率 {usage_pct:.1f}%)"
            )

        return None

    @staticmethod
    def get_approval_info(invoice: ExpenseInvoice) -> dict:
        """計算發票的審核層級資訊"""
        status = invoice.status
        amount = Decimal(str(invoice.amount)) if invoice.amount else Decimal("0")
        is_high_value = amount > APPROVAL_THRESHOLD

        level_map = {
            "pending": "pending",
            "pending_receipt": "pending",
            "manager_approved": "manager",
            "finance_approved": "finance",
            "verified": "final",
            "rejected": None,
        }

        next_map: dict[str, Optional[str]] = {
            "pending": "manager",
            "pending_receipt": "manager",
            "manager_approved": "finance" if is_high_value else "final",
            "finance_approved": "final",
            "verified": None,
            "rejected": None,
        }

        return {
            "approval_level": level_map.get(status),
            "next_approval": next_map.get(status),
        }
