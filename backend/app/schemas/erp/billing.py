"""ERP 請款 Schemas"""
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ERPBillingCreate(BaseModel):
    """建立請款"""
    erp_quotation_id: int
    billing_code: Optional[str] = Field(None, max_length=20, description="系統請款編碼 BL_{yyyy}_{NNN}")
    billing_period: Optional[str] = Field(None, max_length=50, description="期別")
    billing_date: date = Field(..., description="請款日期")
    billing_amount: Decimal = Field(..., description="請款金額")
    payment_status: str = Field("pending", description="狀態")
    notes: Optional[str] = None


class ERPBillingUpdate(BaseModel):
    """更新請款"""
    billing_period: Optional[str] = Field(None, max_length=50)
    billing_date: Optional[date] = None
    billing_amount: Optional[Decimal] = None
    payment_status: Optional[str] = None
    payment_date: Optional[date] = None
    payment_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class ERPBillingResponse(BaseModel):
    """請款完整資訊"""
    id: int
    erp_quotation_id: int
    billing_code: Optional[str] = None
    billing_period: Optional[str] = None
    billing_date: date
    billing_amount: Decimal
    payment_status: str = "pending"
    payment_date: Optional[date] = None
    payment_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 關聯顯示
    invoice_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
