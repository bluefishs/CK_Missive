"""ERP 發票 Schemas"""
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ERPInvoiceCreate(BaseModel):
    """建立發票"""
    erp_quotation_id: int
    invoice_number: str = Field(..., max_length=50, description="發票號碼")
    invoice_date: date = Field(..., description="開立日期")
    amount: Decimal = Field(..., description="金額 (含稅)")
    tax_amount: Decimal = Field(Decimal("0"), description="稅額")
    invoice_type: str = Field("sales", description="類型: sales/purchase")
    description: Optional[str] = Field(None, max_length=300)
    billing_id: Optional[int] = Field(None, description="關聯請款期別 ID")
    notes: Optional[str] = None


class CreateFromBillingRequest(BaseModel):
    """從請款記錄開立發票"""
    billing_id: int
    invoice_number: str = Field(..., max_length=50, description="發票號碼")
    invoice_date: Optional[date] = Field(None, description="開立日期 (預設今天)")
    notes: Optional[str] = None


class ERPInvoiceUpdate(BaseModel):
    """更新發票"""
    invoice_number: Optional[str] = Field(None, max_length=50)
    invoice_date: Optional[date] = None
    amount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    invoice_type: Optional[str] = None
    description: Optional[str] = Field(None, max_length=300)
    status: Optional[str] = None
    notes: Optional[str] = None


class InvoiceSummaryRequest(BaseModel):
    """跨案件發票彙總查詢"""
    invoice_type: Optional[str] = Field(None, description="類型: sales/purchase")
    year: Optional[int] = Field(None, description="年度 (民國)")
    skip: int = 0
    limit: int = 50


class ERPInvoiceResponse(BaseModel):
    """發票完整資訊"""
    id: int
    erp_quotation_id: int
    invoice_number: str
    invoice_date: date
    amount: Decimal
    tax_amount: Decimal = Decimal("0")
    invoice_type: str = "sales"
    description: Optional[str] = None
    status: str = "issued"
    billing_id: Optional[int] = None
    voided_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
