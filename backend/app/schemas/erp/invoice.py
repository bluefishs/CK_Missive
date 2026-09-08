"""ERP 發票 Schemas"""
from typing import Literal, Optional
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
    # 2026-09-08（第二版）owner：「課稅別改對應選取發票種類（三聯／二聯），
    # 因為原用意是書寫發票所需數據，係由發票金額反算稅額(發票)與銷售額(發票)」。
    #
    # 第一版把「聯式」與「課稅別」混成一個選項（「免稅／零稅率（二聯式）」）——
    # 而 owner 提供的實體發票 EE15019500（買受人桃園市政府工務局）是**二聯式且應稅**，
    # 照那個標籤選會讓機關的二聯式發票被記成免稅、少掉 5% 的稅。
    #
    # 真正要填的是**發票種類**（決定聯式與要不要買受人統編），而銷售額與稅額
    # 一律**由發票金額反算**（總表的實例：MT18585759 金額 15,000 ⇒ 銷售額 14,286、稅額 714）。
    invoice_kind: Literal["triplicate", "duplicate"] = Field(
        "triplicate", description="triplicate=三聯式（營業人，需統編）／duplicate=二聯式（機關或個人）"
    )
    #: 零稅率／免稅仍然存在，但那是**課稅別**不是聯式 —— 兩者獨立，預設應稅。
    tax_exempt: bool = Field(False, description="零稅率／免稅（與聯式無關）")
    buyer_name: Optional[str] = Field(None, max_length=200, description="發票抬頭（買受人）")
    buyer_tax_id: Optional[str] = Field(None, max_length=20, description="買受人統編")
    invoice_remark: Optional[str] = Field(None, max_length=200, description="發票備註（印在發票上）")


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
    year: Optional[int] = Field(None, description="年度（西元；比對發票開立日期）")
    # 2026-09-07 owner：「CK2025_PM、QT2025_001 也無處可查」——一次搜四個欄位，
    # 因為人手上拿到的可能是發票號、案號、報價單號或案名裡的任何一個。
    search: Optional[str] = Field(None, max_length=100, description="發票號／案號／報價單號／案名")
    #: 2026-09-09 owner「表頭篩選請完善」：欄位早就標了 `sorter: true`，
    #: 而**後端沒有這兩個參數** ⇒ 那些排序箭頭是裝飾品，點了什麼都不會發生。
    #: 允許的欄位由 repository 用白名單解析（sort_utils），不接受任意字串。
    sort_by: Optional[str] = Field(None, description="排序欄位（invoice_number／invoice_date／amount）")
    sort_order: Optional[str] = Field("desc", description="asc／desc")
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
    #: 2026-09-08：總表「發票明細」本來就有這四項，此前只能塞在備註文字裡。
    #: ⚠️ Pydantic 對 schema 沒宣告的欄位是**靜默丟棄**（weekly 61 的形狀）——
    #: ORM 加了欄位而 Response 沒加，前端永遠看不到，且不會有任何錯誤。
    invoice_kind: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    invoice_remark: Optional[str] = None
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


class LinkInvoiceToBillingRequest(BaseModel):
    """把已登錄（billing_id 為空）的發票關聯到請款——2026-09-04 owner：152 的發票在報價單上、分頁卻說沒發票"""
    invoice_id: int
    billing_id: int
