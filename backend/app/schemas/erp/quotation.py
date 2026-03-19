"""ERP 報價/成本主檔 Schemas"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.schemas.common import BaseQueryParams


class ERPQuotationCreate(BaseModel):
    """建立報價"""
    case_code: Optional[str] = Field(None, max_length=50, description="案號 (未提供時自動產生)")
    case_name: Optional[str] = Field(None, max_length=500, description="案名")
    year: Optional[int] = Field(None, description="年度 (民國)")
    total_price: Optional[Decimal] = Field(None, description="總價 (含稅)")
    tax_amount: Decimal = Field(Decimal("0"), description="稅額")
    outsourcing_fee: Decimal = Field(Decimal("0"), description="外包費")
    personnel_fee: Decimal = Field(Decimal("0"), description="人事費")
    overhead_fee: Decimal = Field(Decimal("0"), description="管銷費")
    other_cost: Decimal = Field(Decimal("0"), description="其他成本")
    budget_limit: Optional[Decimal] = Field(None, description="預算上限")
    status: str = Field("draft", description="狀態")
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_profit_margin(self) -> "ERPQuotationCreate":
        """毛利率卡控 — 成本不得超過總價 (負毛利攔截)"""
        price = self.total_price
        if price is None or price <= 0:
            return self
        total_cost = (
            (self.outsourcing_fee or Decimal("0"))
            + (self.personnel_fee or Decimal("0"))
            + (self.overhead_fee or Decimal("0"))
            + (self.other_cost or Decimal("0"))
        )
        tax = self.tax_amount if self.tax_amount else Decimal("0")
        revenue = price - tax
        if revenue > 0 and total_cost > revenue:
            margin_pct = ((revenue - total_cost) / revenue * 100).quantize(Decimal("0.1"))
            raise ValueError(
                f"預估毛利率為 {margin_pct}%，成本 ({total_cost:,.0f}) 超過營收 ({revenue:,.0f})，"
                f"請確認報價或申請主管特別簽核"
            )
        return self


class ERPQuotationUpdate(BaseModel):
    """更新報價"""
    case_code: Optional[str] = Field(None, max_length=50)
    case_name: Optional[str] = Field(None, max_length=500)
    year: Optional[int] = None
    total_price: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    outsourcing_fee: Optional[Decimal] = None
    personnel_fee: Optional[Decimal] = None
    overhead_fee: Optional[Decimal] = None
    other_cost: Optional[Decimal] = None
    budget_limit: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ERPQuotationResponse(BaseModel):
    """報價完整資訊 (含計算欄位)"""
    id: int
    case_code: str
    case_name: Optional[str] = None
    year: Optional[int] = None
    total_price: Optional[Decimal] = None
    tax_amount: Decimal = Decimal("0")
    outsourcing_fee: Decimal = Decimal("0")
    personnel_fee: Decimal = Decimal("0")
    overhead_fee: Decimal = Decimal("0")
    other_cost: Decimal = Decimal("0")
    status: str = "draft"
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 預算
    budget_limit: Optional[Decimal] = None
    budget_usage_pct: Optional[Decimal] = Field(None, description="預算使用率(%)")
    is_over_budget: bool = Field(False, description="是否超出預算")

    # 計算欄位 (由 Service 層填充)
    total_cost: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    gross_margin: Optional[Decimal] = Field(None, description="毛利率 (%)")
    net_profit: Decimal = Decimal("0")

    # 聚合欄位
    invoice_count: int = 0
    billing_count: int = 0
    total_billed: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    total_payable: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)


class ERPQuotationListRequest(BaseQueryParams):
    """報價列表查詢"""
    year: Optional[int] = Field(None, description="年度篩選")
    status: Optional[str] = Field(None, description="狀態篩選")
    case_code: Optional[str] = Field(None, description="案號篩選")


class ERPProfitSummary(BaseModel):
    """損益摘要"""
    total_revenue: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    total_gross_profit: Decimal = Decimal("0")
    avg_gross_margin: Optional[Decimal] = None
    total_billed: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    total_outstanding: Decimal = Decimal("0")
    case_count: int = 0
    by_year: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ERPProfitTrendItem(BaseModel):
    """年度損益趨勢項目"""
    year: int
    revenue: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    gross_margin: Optional[Decimal] = None
    case_count: int = 0

    model_config = ConfigDict(from_attributes=True)
