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


class MonthlyTrendRequest(BaseModel):
    """月度收支趨勢請求"""
    months: int = Field(default=12, ge=1, le=36, description="回溯月數")
    case_code: Optional[str] = Field(None, description="指定案號 (空=全公司)")


class MonthlyTrendItem(BaseModel):
    """單月收支"""
    month: str = Field(..., description="YYYY-MM 格式")
    income: Decimal = Decimal("0")
    expense: Decimal = Decimal("0")
    net: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)


class MonthlyTrendResponse(BaseModel):
    """月度收支趨勢回應"""
    months: List[MonthlyTrendItem]
    case_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BudgetRankingRequest(BaseModel):
    """預算使用率排行請求"""
    top_n: int = Field(default=15, ge=1, le=50, description="Top N")
    order: str = Field(default="desc", pattern="^(asc|desc)$", description="排序方向")


class BudgetRankingItem(BaseModel):
    """專案預算使用率"""
    case_code: str
    case_name: Optional[str] = None
    budget_total: Optional[Decimal] = None
    total_expense: Decimal = Decimal("0")
    total_income: Decimal = Decimal("0")
    usage_pct: Optional[float] = None
    alert: str = "normal"

    model_config = ConfigDict(from_attributes=True)


class BudgetRankingResponse(BaseModel):
    """預算使用率排行回應"""
    items: List[BudgetRankingItem]
    total_projects: int = 0

    model_config = ConfigDict(from_attributes=True)


class ExportExpensesRequest(BaseModel):
    """匯出費用報銷 Excel"""
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    case_code: Optional[str] = None
    status: Optional[str] = None


class ExportLedgerRequest(BaseModel):
    """匯出帳本 Excel"""
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    case_code: Optional[str] = None
    entry_type: Optional[str] = None
