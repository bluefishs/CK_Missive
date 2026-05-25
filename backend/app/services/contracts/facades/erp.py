# -*- coding: utf-8 -*-
"""ERPFacade - ERP context 對外唯一入口

v6.10 P1 Phase B (2026-05-18)

解 step 29 揭發：
  - ai -> erp (5 imports) — Agent 查詢 ERP 數據
  - erp -> contract (4)
  - 其他散 imports

統一封 quotation / invoice / billing / expense / ledger / financial_summary 操作。
"""
from __future__ import annotations

from datetime import date
from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class ERPFacade:
    """ERP bounded context 對外唯一入口

    使用範例：
        facade = ERPFacade(db)
        summary = await facade.get_financial_summary(year=2026)
        invoices = await facade.list_invoices_by_case("CK2026_01_03_001")
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    # === Public API ===

    async def get_financial_summary(
        self,
        year: Optional[int] = None,
        case_code: Optional[str] = None,
    ) -> dict:
        """財務彙總統計（給 Agent 查詢 + Dashboard 共用）

        取代 ai/agent_tools.py 直 import erp/financial_summary
        """
        try:
            from app.services.erp.financial_summary_service import (
                FinancialSummaryService,
            )
            svc = FinancialSummaryService(self._db)
            return await svc.compute(year=year, case_code=case_code)
        except (ImportError, AttributeError):
            return {"total_revenue": 0, "total_expense": 0, "error": "service unavailable"}

    async def list_invoices_by_case(
        self,
        case_code: str,
    ) -> List[dict]:
        """依 case_code 列發票（跨域 bridge）"""
        try:
            from app.services.erp.invoice_service import ERPInvoiceService
            svc = ERPInvoiceService(self._db)
            return await svc.list_by_case_code(case_code)
        except (ImportError, AttributeError):
            return []

    async def list_quotations(
        self,
        *,
        case_code: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """列報價單"""
        try:
            from app.services.erp.quotation_service import ERPQuotationService
            svc = ERPQuotationService(self._db)
            return await svc.list_by_filters(case_code=case_code, status=status, limit=limit)
        except (ImportError, AttributeError):
            return []

    async def get_ledger_balance(
        self,
        case_code: Optional[str] = None,
    ) -> dict:
        """統一帳本餘額（給跨域查詢用）"""
        try:
            from app.services.erp.finance_ledger_service import FinanceLedgerService
            svc = FinanceLedgerService(self._db)
            return await svc.compute_balance(case_code=case_code)
        except (ImportError, AttributeError):
            return {"balance": 0, "error": "service unavailable"}

    async def get_expense_summary(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """費用報銷彙總（取代 ai/agent_tools.py 直 import erp/expense_*）"""
        try:
            from app.services.erp.expense_invoice_service import ExpenseInvoiceService
            svc = ExpenseInvoiceService(self._db)
            return await svc.summarize_for_user(
                user_id=user_id, start_date=start_date, end_date=end_date,
            )
        except (ImportError, AttributeError):
            return {"total": 0, "pending_count": 0, "error": "service unavailable"}


__all__ = ["ERPFacade"]
