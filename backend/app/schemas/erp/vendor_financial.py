"""廠商財務彙總 Schemas

Version: 1.0.0
Created: 2026-03-22
"""
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class VendorFinancialSummary(BaseModel):
    """廠商財務彙總"""
    vendor_id: int
    vendor_name: str
    vendor_code: Optional[str] = None

    # 應付帳款
    total_payable: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    pending_payable: Decimal = Decimal("0")
    payable_count: int = 0

    # 報銷發票 (透過 seller_ban 配對)
    total_expenses: Decimal = Decimal("0")
    expense_count: int = 0

    # 帳本 (直接 vendor_id 關聯)
    ledger_expense_total: Decimal = Decimal("0")
    ledger_entry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class VendorFinancialSummaryRequest(BaseModel):
    """廠商財務彙總查詢"""
    vendor_id: int
    year: Optional[int] = None
