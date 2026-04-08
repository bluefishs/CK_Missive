# -*- coding: utf-8 -*-
"""
案件全流程鏈追蹤器

以 case_code 為樞紐，一次查詢完整業務鏈路：
tender → pm_case → quotation → invoice → billing → vendor_payable → expense → ledger

Version: 1.0.0
Created: 2026-04-08
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CaseFlowTracker:
    """案件全流程鏈查詢"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_full_flow(self, case_code: str) -> Dict[str, Any]:
        """
        以 case_code 查詢完整業務鏈路。

        Returns:
            {
                "case_code": "CK2025_FN_01_001",
                "tender": {...} or null,
                "pm_case": {...} or null,
                "quotation": {...} or null,
                "invoices": [...],
                "billings": [...],
                "vendor_payables": [...],
                "expenses": [...],
                "ledger_entries": [...],
                "flow_summary": {...},
            }
        """
        result: Dict[str, Any] = {"case_code": case_code}

        # PM Case
        result["pm_case"] = await self._get_pm_case(case_code)

        # ERP Quotation
        result["quotation"] = await self._get_quotation(case_code)

        quotation_id = result["quotation"].get("id") if result["quotation"] else None

        # Invoices + Billings + Vendor Payables (from quotation)
        result["invoices"] = await self._get_invoices(quotation_id) if quotation_id else []
        result["billings"] = await self._get_billings(quotation_id) if quotation_id else []
        result["vendor_payables"] = await self._get_vendor_payables(quotation_id) if quotation_id else []

        # Expenses (by case_code)
        result["expenses"] = await self._get_expenses(case_code)

        # Tender (by case_code link)
        result["tender"] = await self._get_tender(case_code)

        # Flow summary
        q_amount = float(result["quotation"]["total_price"]) if result["quotation"] and result["quotation"].get("total_price") else 0
        billed = sum(float(b.get("billing_amount", 0)) for b in result["billings"])
        paid = sum(float(v.get("paid_amount", 0) or 0) for v in result["vendor_payables"])
        expensed = sum(float(e.get("amount", 0)) for e in result["expenses"])

        result["flow_summary"] = {
            "quotation_amount": q_amount,
            "billed_amount": billed,
            "vendor_paid": paid,
            "expenses_total": expensed,
            "has_tender": result["tender"] is not None,
            "has_pm_case": result["pm_case"] is not None,
            "invoice_count": len(result["invoices"]),
            "billing_count": len(result["billings"]),
            "stage": self._determine_stage(result),
        }

        return result

    def _determine_stage(self, result: Dict) -> str:
        if result["billings"]:
            return "billing"
        if result["invoices"]:
            return "invoiced"
        if result["quotation"]:
            return "quoted"
        if result["pm_case"]:
            return "case_created"
        if result["tender"]:
            return "tender_found"
        return "unknown"

    async def _get_pm_case(self, case_code: str) -> Optional[Dict]:
        from app.extended.models.core import ContractProject
        row = (await self.db.execute(
            select(ContractProject).where(ContractProject.case_code == case_code).limit(1)
        )).scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id, "case_code": row.case_code,
            "project_code": row.project_code,
            "name": row.name, "status": row.status,
        }

    async def _get_quotation(self, case_code: str) -> Optional[Dict]:
        from app.extended.models.erp import ERPQuotation
        row = (await self.db.execute(
            select(ERPQuotation)
            .where(ERPQuotation.case_code == case_code)
            .where(ERPQuotation.deleted_at.is_(None))
            .limit(1)
        )).scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id, "case_code": row.case_code, "case_name": row.case_name,
            "total_price": float(row.total_price) if row.total_price else 0,
            "status": row.status, "year": row.year,
        }

    async def _get_invoices(self, quotation_id: int):
        from app.extended.models.erp import ERPInvoice
        rows = (await self.db.execute(
            select(ERPInvoice).where(ERPInvoice.erp_quotation_id == quotation_id)
        )).scalars().all()
        return [
            {"id": r.id, "invoice_number": r.invoice_number,
             "amount": float(r.amount) if r.amount else 0, "status": r.status}
            for r in rows
        ]

    async def _get_billings(self, quotation_id: int):
        from app.extended.models.erp import ERPBilling
        rows = (await self.db.execute(
            select(ERPBilling).where(ERPBilling.erp_quotation_id == quotation_id)
        )).scalars().all()
        return [
            {"id": r.id, "billing_code": r.billing_code,
             "billing_amount": float(r.billing_amount) if r.billing_amount else 0,
             "payment_status": r.payment_status, "billing_period": r.billing_period}
            for r in rows
        ]

    async def _get_vendor_payables(self, quotation_id: int):
        from app.extended.models.erp import ERPVendorPayable
        rows = (await self.db.execute(
            select(ERPVendorPayable).where(ERPVendorPayable.erp_quotation_id == quotation_id)
        )).scalars().all()
        return [
            {"id": r.id, "vendor_name": r.vendor_name,
             "payable_amount": float(r.payable_amount) if r.payable_amount else 0,
             "paid_amount": float(r.paid_amount) if r.paid_amount else 0,
             "payment_status": r.payment_status}
            for r in rows
        ]

    async def _get_expenses(self, case_code: str):
        from app.extended.models.invoice import ExpenseInvoice
        rows = (await self.db.execute(
            select(ExpenseInvoice).where(ExpenseInvoice.case_code == case_code).limit(50)
        )).scalars().all()
        return [
            {"id": r.id, "inv_num": r.inv_num,
             "amount": float(r.amount) if r.amount else 0,
             "category": r.category, "status": r.status}
            for r in rows
        ]

    async def _get_tender(self, case_code: str) -> Optional[Dict]:
        """嘗試從 PM Case 的 tender_job_number 找到標案"""
        from app.extended.models.core import ContractProject
        pm = (await self.db.execute(
            select(ContractProject).where(ContractProject.case_code == case_code).limit(1)
        )).scalar_one_or_none()
        if not pm or not getattr(pm, "tender_job_number", None):
            return None

        from app.extended.models.tender_cache import TenderRecord
        tender = (await self.db.execute(
            select(TenderRecord).where(TenderRecord.job_number == pm.tender_job_number).limit(1)
        )).scalar_one_or_none()
        if not tender:
            return None
        return {
            "job_number": tender.job_number, "title": tender.title,
            "unit_name": tender.unit_name,
            "budget": float(tender.budget) if tender.budget else 0,
        }
