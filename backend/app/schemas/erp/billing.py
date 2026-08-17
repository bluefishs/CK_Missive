"""ERP 請款 Schemas"""
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ERPBillingCreate(BaseModel):
    """建立請款"""
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
    billing_code: Optional[str] = Field(None, max_length=20, description="系統請款編碼 BL_{yyyy}_{NNN}")
    billing_period: Optional[str] = Field(None, max_length=50, description="期別")
    billing_date: date = Field(..., description="請款日期")
    billing_amount: Decimal = Field(..., description="請款金額")
    payment_status: str = Field("pending", description="狀態")

    # 2026-08-17：補上這兩欄。
    #
    # 前端建立表單**一直在送** `payment_amount` 與 `payment_date`
    # （見 ERPAccountRecordFormPage 的 payload），而這個 schema 沒有它們
    # → **Pydantic 靜默丟棄** → DB 存下「payment_status='paid' 而金額是 null」
    # → 統計卡「已收款額」顯示 **0**，而請款總額 3,383 萬。
    #
    # 實測全庫 15 筆都是這樣來的。這是同一天第三次踩到同一個形狀
    # （quotation_no 到不了 API／待填報連結沒人接）：
    # **送出端與接收端各說各話，而兩邊都不會報錯。**
    payment_amount: Optional[Decimal] = Field(None, description="收款金額")
    payment_date: Optional[date] = Field(None, description="收款日期")

    notes: Optional[str] = None


class ERPBillingUpdate(BaseModel):
    """更新請款"""
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
