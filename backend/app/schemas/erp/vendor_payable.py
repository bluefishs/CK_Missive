"""ERP 廠商應付 Schemas"""
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ERPVendorPayableCreate(BaseModel):
    """建立廠商應付"""
    erp_quotation_id: int
    vendor_name: str = Field(..., max_length=200, description="廠商名稱")
    vendor_code: Optional[str] = Field(None, max_length=50, description="廠商代碼")
    payable_amount: Decimal = Field(..., description="應付金額")
    description: Optional[str] = Field(None, max_length=300)
    due_date: Optional[date] = None
    invoice_number: Optional[str] = Field(None, max_length=50, description="廠商發票號碼")
    notes: Optional[str] = None


class ERPVendorPayableUpdate(BaseModel):
    """更新廠商應付"""
    vendor_name: Optional[str] = Field(None, max_length=200)
    vendor_code: Optional[str] = Field(None, max_length=50)
    payable_amount: Optional[Decimal] = None
    description: Optional[str] = Field(None, max_length=300)
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    paid_amount: Optional[Decimal] = None
    payment_status: Optional[str] = None
    invoice_number: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class ERPVendorPayableResponse(BaseModel):
    """廠商應付完整資訊"""
    id: int
    erp_quotation_id: int
    vendor_name: str
    vendor_code: Optional[str] = None
    payable_amount: Decimal
    description: Optional[str] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    paid_amount: Optional[Decimal] = None
    payment_status: str = "unpaid"
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
