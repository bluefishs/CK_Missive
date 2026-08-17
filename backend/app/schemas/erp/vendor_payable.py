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
    vendor_id: Optional[int] = Field(None, description="廠商 ID (自動配對)")
    payable_amount: Decimal = Field(..., description="應付金額")
    description: Optional[str] = Field(None, max_length=300)
    due_date: Optional[date] = None
    invoice_number: Optional[str] = Field(None, max_length=50, description="廠商發票號碼")

    # 2026-08-17：補上這三欄（同 billing 的形狀，但這裡**更嚴重**）。
    #
    # 前端建立表單一直在送 `payment_status` / `paid_date` / `paid_amount`，
    # 而這個 schema **連 payment_status 都沒有** → 全部被 Pydantic 靜默丟棄
    # → 建立時選「已付款」完全無效，一律落回 model 預設。
    #
    # 使用者的操作沒有任何效果，而且不會有任何錯誤訊息。
    payment_status: Optional[str] = Field(None, description="付款狀態")
    paid_amount: Optional[Decimal] = Field(None, description="已付金額")
    paid_date: Optional[date] = Field(None, description="付款日期")

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
    vendor_id: Optional[int] = None
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
