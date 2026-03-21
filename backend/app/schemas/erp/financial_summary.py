from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
import datetime
from typing import Optional, List, Dict
from decimal import Decimal

class ProjectFinancialSummary(BaseModel):
    """單一專案財務彙總"""
    case_code: str
    case_name: Optional[str] = None

    budget_total: Optional[Decimal] = None
    quotation_total: Optional[Decimal] = None

    billed_amount: Decimal = Decimal("0")
    received_amount: Decimal = Decimal("0")

    vendor_payable_total: Decimal = Decimal("0")
    vendor_paid_total: Decimal = Decimal("0")

    expense_invoice_count: int = 0
    expense_invoice_total: Decimal = Decimal("0")

    total_income: Decimal = Decimal("0")
    total_expense: Decimal = Decimal("0")
    net_balance: Decimal = Decimal("0")

    budget_used_percentage: Optional[float] = None
    budget_alert: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class CompanyFinancialOverview(BaseModel):
    """全公司財務總覽"""
    period_start: datetime.date
    period_end: datetime.date

    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal

    expense_by_category: Dict[str, Decimal]
    project_expense: Decimal
    operation_expense: Decimal

    top_projects: List[ProjectFinancialSummary]

    model_config = ConfigDict(from_attributes=True)


class ProjectSummaryRequest(BaseModel):
    """單一專案財務彙總請求"""
    case_code: str = Field(..., max_length=50, description="案號")


class AllProjectsSummaryRequest(BaseModel):
    """所有專案財務一覽請求"""
    year: Optional[int] = Field(None, description="民國年度")
    skip: int = 0
    limit: int = 50


class CompanyOverviewRequest(BaseModel):
    """全公司財務總覽請求"""
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    year: Optional[int] = Field(None, description="民國年度")
    top_n: int = Field(default=10, description="Top N 專案")
