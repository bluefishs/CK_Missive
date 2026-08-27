"""ERP 廠商應付 Schemas"""
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
# 期別詞彙表唯一定義處在應收那一支 —— 不另建第二份
from app.schemas.erp.billing import BillingPeriod
from pydantic import BaseModel, Field, ConfigDict


class ERPVendorPayableCreate(BaseModel):
    """建立廠商應付"""
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
    vendor_name: str = Field(..., max_length=200, description="廠商名稱")
    vendor_code: Optional[str] = Field(None, max_length=50, description="廠商代碼")
    vendor_id: Optional[int] = Field(None, description="廠商 ID (自動配對)")
    payable_amount: Decimal = Field(..., description="應付金額")
    # 2026-08-18 owner：「應收與應付兩者設計不一致」——
    # 期別值域與應收共用（`schemas/erp/billing.py: BillingPeriod`），
    # 寫入端收緊、讀取端寬鬆（ENUM_STORAGE_CONVENTION 規則 3）。
    payable_period: Optional[BillingPeriod] = Field(None, description="期別")
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

    vendor_name: Optional[str] = Field(None, max_length=200)
    vendor_code: Optional[str] = Field(None, max_length=50)
    payable_amount: Optional[Decimal] = None
    payable_period: Optional[BillingPeriod] = Field(None, description="期別")
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
    # 2026-08-27（V4 統一源頭）：有 `vendor_id` 時，上面的 `vendor_name`
    # 一律以 **FK 指向的 partner_vendors 為準**（單一來源）。
    # 而應付單自存的那份文字若與之不同，放這裡 —— **不能靜靜蓋掉**：
    # 實測 3 筆對不上，其中「林晉廷」vs FK 的「林宥廷測量技師事務所」
    # **是不同的人**，若 FK 才是錯的那一邊，蓋掉就等於把錯誤變成唯一事實。
    # ⇒ 兩個都給，讓畫面說得出「這裡有出入」。None 代表兩者一致。
    vendor_name_recorded: Optional[str] = Field(
        None, description="應付單自存的廠商名（僅在與 FK 不同時有值）")
    vendor_code: Optional[str] = None
    vendor_id: Optional[int] = None
    payable_amount: Decimal
    # 讀取端保持寬鬆（str 而非 Literal）：萬一將來有清單外的歷史值，
    # 顯示不該因此壞掉。
    payable_period: Optional[str] = None
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
