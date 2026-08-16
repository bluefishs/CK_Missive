from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict, model_validator
import datetime
from typing import Optional, List, Literal
import os
from decimal import Decimal

# 費用分類枚舉 — 新增分類請同步更新此處與 ledger.py
EXPENSE_CATEGORIES = Literal[
    "交通費", "差旅費", "文具及印刷", "郵電費", "水電費",
    "保險費", "租金", "維修費", "雜費", "設備採購",
    "外包及勞務", "訓練費", "材料費", "報銷及費用", "其他",
]

# 憑證類型
VOUCHER_TYPES = Literal["invoice", "receipt", "ticket", "utility", "other"]

VOUCHER_TYPE_LABELS = {
    "invoice": "統一發票",
    "receipt": "普通收據",
    "ticket": "車票/機票",
    "utility": "水電/電信帳單",
    "other": "其他憑證",
}

# 支援幣別 (ISO 4217)
SUPPORTED_CURRENCIES = Literal["TWD", "USD", "CNY", "JPY", "EUR"]

# === Phase 5-5: 多層審核狀態機 ===
# 狀態定義
EXPENSE_STATUS = Literal[
    "pending",            # 待主管審核
    "pending_receipt",    # 待上傳收據 (財政部同步)
    "manager_approved",   # 主管已核准 (≤30K → verified; >30K → 待財務)
    "finance_approved",   # 財務已核准 (>30K 才有此階段)
    "verified",           # 最終通過 (已入帳)
    "rejected",           # 已駁回
]

# 金額門檻 (TWD): 超過此金額需三級審核
APPROVAL_THRESHOLD = Decimal("30000")

# 2026-08-16：低額自動通過門檻。
#
# 實測核銷金額分布：**中位數 940 元**，9 筆裡 5 筆在 2,000 以下、
# 只有 2 筆超過 30,000。而在此之前的「四層審批」對每一筆一視同仁 ——
# 一張 300 元的計程車收據要走四次點擊，而每一層都是同一組人、
# 沒有角色區分、沒有防自核，**做了也不產生控制效果**。
# 結果是 9 筆只有 2 筆走完：不是大家偷懶，是流程與風險不成比例。
#
# 設 2,000 是依實測分布取的（涵蓋約 5/9），刻意**不設更高**：
# 門檻越高省的力氣越多，但一旦出事的金額也越大。
# 這個數字應該隨實際使用回頭調整，而不是一次定死。
# 設為 0 即關閉自動通過（例如稽核期間）。
AUTO_APPROVE_BELOW = Decimal(os.getenv("EXPENSE_AUTO_APPROVE_BELOW", "2000"))

# 預算警告門檻 (百分比): 累計支出佔預算比率超過此值則預警
BUDGET_WARNING_PCT = Decimal("80")
# 預算攔截門檻 (百分比): 超過此值則攔截審核，需總經理介入
BUDGET_BLOCK_PCT = Decimal("100")

# 狀態流轉規則 (current_status → 允許的下一狀態)
APPROVAL_TRANSITIONS: dict[str, list[str]] = {
    # 2026-08-16 加入 "verified"：低額（≤ AUTO_APPROVE_BELOW）直達終態。
    # 沒有這一項，_determine_next_approval 回 verified 會被
    # 「非法狀態流轉」擋掉 —— 加了但不會生效。
    "pending":           ["manager_approved", "verified", "rejected"],
    "pending_receipt":   ["pending", "rejected"],
    "manager_approved":  ["finance_approved", "verified", "rejected"],
    "finance_approved":  ["verified", "rejected"],
    "verified":          [],   # 終態
    "rejected":          [],   # 終態
}

class ExpenseInvoiceItemBase(BaseModel):
    item_name: str = Field(..., max_length=200, description="品名")
    qty: Decimal = Field(default=1, gt=0, description="數量")
    unit_price: Decimal = Field(..., max_digits=15, decimal_places=2, description="單價")
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2, description="小計")

class ExpenseInvoiceItemCreate(ExpenseInvoiceItemBase):
    pass

class ExpenseInvoiceItemResponse(ExpenseInvoiceItemBase):
    id: int
    invoice_id: int
    
    model_config = ConfigDict(from_attributes=True)

class ExpenseInvoiceBase(BaseModel):
    voucher_type: VOUCHER_TYPES = Field("invoice", description="憑證類型: invoice/receipt/ticket/utility/other")
    inv_num: str = Field(..., min_length=1, max_length=50, description="憑證編號 (發票號碼/收據編號/票號)")
    date: datetime.date = Field(..., description="開立日期 (西元)")
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2, description="總金額 (含稅, TWD 本位幣)")
    tax_amount: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description="稅額")
    buyer_ban: Optional[str] = Field(None, min_length=8, max_length=8, description="買方統編 (8碼)")
    seller_ban: Optional[str] = Field(None, min_length=8, max_length=8, description="賣方統編 (8碼)")
    case_code: Optional[str] = Field(None, max_length=50, description="案號 (NULL=一般營運支出)")
    category: Optional[EXPENSE_CATEGORIES] = Field(None, description="費用分類")
    source: Literal["qr_scan", "manual", "api", "ocr", "mof_sync", "line_upload", "smart_qr", "smart_ocr", "smart_camera"] = "manual"
    notes: Optional[str] = Field(None, max_length=500, description="備註")
    currency: SUPPORTED_CURRENCIES = Field("TWD", description="幣別 (ISO 4217)")
    original_amount: Optional[Decimal] = Field(None, gt=0, max_digits=15, decimal_places=2, description="原始幣別金額")
    exchange_rate: Optional[Decimal] = Field(None, gt=0, max_digits=10, decimal_places=6, description="匯率 (原幣×匯率=TWD)")

class ExpenseInvoiceCreate(ExpenseInvoiceBase):
    """費用報銷發票建立 (QR 自動填入或手動輸入)"""
    attribution_type: Optional[str] = Field("none", description="歸屬類型: project/operational/none")
    operational_account_id: Optional[int] = Field(None, description="營運帳目 ID")
    items: Optional[List[ExpenseInvoiceItemCreate]] = None
    receipt_image_path: Optional[str] = Field(None, description="收據影像路徑")

    @model_validator(mode="after")
    def validate_amount_gte_tax(self) -> "ExpenseInvoiceCreate":
        """含稅總額必須 ≥ 稅額"""
        if self.tax_amount is not None and self.amount < self.tax_amount:
            raise ValueError(f"含稅總額 ({self.amount}) 不可小於稅額 ({self.tax_amount})")
        return self

    @model_validator(mode="after")
    def validate_inv_num_format(self) -> "ExpenseInvoiceCreate":
        """統一發票格式僅在 voucher_type=invoice 時強制驗證"""
        import re
        if self.voucher_type == "invoice":
            if not re.match(r'^[A-Z]{2}\d{8}$', self.inv_num):
                raise ValueError("統一發票號碼格式錯誤，應為 2 英文 + 8 數字 (如 AB12345678)")
        return self

    @model_validator(mode="after")
    def validate_multi_currency(self) -> "ExpenseInvoiceCreate":
        """非 TWD 幣別時，original_amount 與 exchange_rate 為必填，自動計算 amount"""
        if self.currency != "TWD":
            if self.original_amount is None:
                raise ValueError("非 TWD 幣別時，original_amount (原始金額) 為必填")
            if self.exchange_rate is None:
                raise ValueError("非 TWD 幣別時，exchange_rate (匯率) 為必填")
            # 自動換算 TWD 本位幣金額 (上方已確認非 None)
            assert self.original_amount is not None and self.exchange_rate is not None
            self.amount = (self.original_amount * self.exchange_rate).quantize(Decimal("0.01"))
        return self

class ExpenseInvoiceUpdate(BaseModel):
    """允許更新少部分資訊或狀態"""
    category: Optional[EXPENSE_CATEGORIES] = Field(None)
    notes: Optional[str] = Field(None, max_length=500)
    status: Optional[EXPENSE_STATUS] = Field(None, description="狀態 (受狀態機規則約束)")

class ExpenseInvoiceResponse(ExpenseInvoiceBase):
    id: int
    user_id: Optional[int]
    status: EXPENSE_STATUS
    attribution_type: str = "none"
    operational_account_id: Optional[int] = None
    source_image_path: Optional[str]
    receipt_image_path: Optional[str] = None
    items: List[ExpenseInvoiceItemResponse] = []
    approval_level: Optional[str] = Field(None, description="當前審核層級")
    next_approval: Optional[str] = Field(None, description="下一審核層級")

    model_config = ConfigDict(from_attributes=True)

class ExpenseInvoiceUpdateRequest(BaseModel):
    """更新報銷發票請求 (含 id + 更新資料)"""
    id: int
    data: ExpenseInvoiceUpdate


class ExpenseInvoiceRejectRequest(BaseModel):
    """駁回報銷請求"""
    id: int
    reason: Optional[str] = Field(None, max_length=500, description="駁回原因")


class ExpenseInvoiceQRScanRequest(BaseModel):
    """QR Code 掃描建立報銷發票"""
    raw_qr: str = Field(..., description="原始 QR Code 字串")
    case_code: Optional[str] = Field(None, max_length=50, description="案號")
    category: Optional[EXPENSE_CATEGORIES] = Field(None, description="費用分類")


class ExpenseInvoiceOCRResponse(BaseModel):
    """OCR 辨識結果回傳"""
    inv_num: Optional[str] = None
    date: Optional[datetime.date] = None
    amount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    buyer_ban: Optional[str] = None
    seller_ban: Optional[str] = None
    raw_text: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="辨識信心度 (0~1)")
    warnings: List[str] = Field(default_factory=list, description="解析警告")
    source_image_path: Optional[str] = None


class ExpenseInvoiceQuery(BaseModel):
    """費用發票多重條件查詢"""
    case_code: Optional[str] = None
    attribution_type: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    user_id: Optional[int] = None
    skip: int = 0
    limit: int = Field(default=20, le=100)


# ---------------------------------------------------------------------------
# 案件整合財務紀錄（case-finance）— 2026-07-31 補契約
# ---------------------------------------------------------------------------
# 立法背景：此端點原本回未綁 response_model 的裸 dict，前端在
# `pages/pmCase/ExpensesTab.tsx` 與 `pages/erpQuotation/ExpensesTab.tsx`
# **各自宣告了一份同名 interface**。後端欄位一改，兩處都要手動跟，
# 漏改會靜默錯位（欄位變 undefined，畫面只是少一格，不會報錯）。
# 這正是當日「同一件事兩份實作」家族的資料契約版本。

class CaseFinanceRecord(BaseModel):
    """案件財務紀錄單列（費用核銷 / 請款 / 開票 三種來源統一形狀）"""
    type: Literal["expense", "billing", "invoice"] = Field(..., description="紀錄種類")
    id: int
    date: Optional[str] = Field(None, description="日期 (YYYY-MM-DD)")
    amount: float
    description: Optional[str] = Field(None, description="發票號碼 / 請款期別 / 發票號")
    category: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = Field(None, description="來源表識別")


class CaseFinanceSummary(BaseModel):
    expense_count: int = 0
    expense_total: float = 0
    billing_count: int = 0
    billing_total: float = 0
    invoice_count: int = 0
    invoice_total: float = 0


class CaseFinanceResponse(BaseModel):
    case_code: str
    records: List[CaseFinanceRecord] = Field(default_factory=list)
    summary: CaseFinanceSummary
