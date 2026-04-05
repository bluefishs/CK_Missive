from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
import datetime
from typing import Optional, Literal
from decimal import Decimal

class LedgerBase(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2, description="金額")
    entry_type: Literal["income", "expense"] = Field(..., description="收入或支出")
    category: Optional[str] = Field(None, max_length=50, description="分類")
    description: Optional[str] = Field(None, max_length=500, description="摘要/說明")
    case_code: Optional[str] = Field(None, max_length=50, description="案號 (NULL=一般營運支出)")
    transaction_date: Optional[datetime.date] = Field(None, description="交易日期")

class LedgerCreate(LedgerBase):
    """手動記帳，不帶自動來源"""
    pass

class LedgerResponse(LedgerBase):
    id: int
    ledger_code: Optional[str] = None
    user_id: Optional[int]
    source_type: str
    source_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class LedgerBalanceRequest(BaseModel):
    """查詢專案收支餘額"""
    case_code: str = Field(..., max_length=50, description="案號")


class LedgerCategoryBreakdownRequest(BaseModel):
    """帳本分類拆解請求"""
    case_code: Optional[str] = Field(None, max_length=50, description="案號")
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    entry_type: Optional[Literal["income", "expense"]] = None


class LedgerQuery(BaseModel):
    """帳本查詢條件"""
    case_code: Optional[str] = None
    entry_type: Optional[Literal["income", "expense"]] = None
    category: Optional[str] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    user_id: Optional[int] = None
    skip: int = 0
    limit: int = Field(default=20, le=100)
