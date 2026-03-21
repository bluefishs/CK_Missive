from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
import datetime
from typing import Optional, List, Literal
from decimal import Decimal

# 費用分類枚舉 — 新增分類請同步更新此處與 ledger.py
EXPENSE_CATEGORIES = Literal[
    "交通費", "差旅費", "文具及印刷", "郵電費", "水電費",
    "保險費", "租金", "維修費", "雜費", "設備採購",
    "外包及勞務", "訓練費", "材料費", "報銷及費用", "其他",
]

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
    inv_num: str = Field(..., min_length=10, max_length=20, pattern=r"^[A-Z]{2}\d{8}$", description="發票號碼 (如 AB12345678)")
    date: datetime.date = Field(..., description="開立日期 (西元)")
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2, description="總金額 (含稅)")
    tax_amount: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2, description="稅額")
    buyer_ban: Optional[str] = Field(None, min_length=8, max_length=8, description="買方統編 (8碼)")
    seller_ban: Optional[str] = Field(None, min_length=8, max_length=8, description="賣方統編 (8碼)")
    case_code: Optional[str] = Field(None, max_length=50, description="案號 (NULL=一般營運支出)")
    category: Optional[EXPENSE_CATEGORIES] = Field(None, description="費用分類")
    source: Literal["qr_scan", "manual", "api", "ocr", "mof_sync"] = "manual"
    notes: Optional[str] = Field(None, max_length=500, description="備註")

class ExpenseInvoiceCreate(ExpenseInvoiceBase):
    """費用報銷發票建立 (QR 自動填入或手動輸入)"""
    items: Optional[List[ExpenseInvoiceItemCreate]] = None

class ExpenseInvoiceUpdate(BaseModel):
    """允許更新少部分資訊或狀態"""
    category: Optional[EXPENSE_CATEGORIES] = Field(None)
    notes: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, max_length=20)

class ExpenseInvoiceResponse(ExpenseInvoiceBase):
    id: int
    user_id: Optional[int]
    status: str
    source_image_path: Optional[str]
    items: List[ExpenseInvoiceItemResponse] = []
    
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


class ExpenseInvoiceQuery(BaseModel):
    """費用發票多重條件查詢"""
    case_code: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    user_id: Optional[int] = None
    skip: int = 0
    limit: int = Field(default=20, le=100)
