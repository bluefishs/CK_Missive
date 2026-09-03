"""ERP 發票 Schemas"""
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ERPInvoiceCreate(BaseModel):
    """建立發票"""
    # 2026-08-17：extra="forbid" —— 送來的欄位若這裡沒有，**立刻 422 並指名**，
    # 而不是被 Pydantic 靜默丟棄。
    #
    # 同日踩了三次同一個形狀：payment_amount / payment_date（請款）與
    # payment_status / paid_amount / paid_date（應付）都被前端送出卻默默不見，
    # 結果是 DB 存下「已收款、金額 null」而統計卡顯示「已收 0」——
    # 三層都沒有人會報錯。
    #
    # 只加在寫入端：Response 加了沒意義，Query 加了會擋掉合法擴充。
    model_config = ConfigDict(extra="forbid")

    erp_quotation_id: int
    invoice_number: str = Field(..., max_length=50, description="發票號碼")
    invoice_ref: Optional[str] = Field(None, max_length=20, description="系統發票參照碼 IV_{yyyy}_{NNN}")
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
    # 2026-08-17：extra="forbid" —— 送來的欄位若這裡沒有，**立刻 422 並指名**，
    # 而不是被 Pydantic 靜默丟棄。
    #
    # 同日踩了三次同一個形狀：payment_amount / payment_date（請款）與
    # payment_status / paid_amount / paid_date（應付）都被前端送出卻默默不見，
    # 結果是 DB 存下「已收款、金額 null」而統計卡顯示「已收 0」——
    # 三層都沒有人會報錯。
    #
    # 只加在寫入端：Response 加了沒意義，Query 加了會擋掉合法擴充。
    model_config = ConfigDict(extra="forbid")

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
    invoice_ref: Optional[str] = None
    invoice_date: date
    amount: Decimal
    tax_amount: Decimal = Decimal("0")
    invoice_type: str = "sales"
    description: Optional[str] = None
    status: str = "issued"
    billing_id: Optional[int] = None
    voided_at: Optional[datetime] = None
    notes: Optional[str] = None
    source: Optional[str] = None  # manual/xls_import/auto_from_billing（2026-09-03）
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
