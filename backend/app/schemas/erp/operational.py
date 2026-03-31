"""營運帳目 Schemas (Operational Account)

帳目主檔 CRUD + 費用明細 CRUD + 統計
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional, Dict

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 常數定義
# ============================================================================

ACCOUNT_CATEGORIES: Dict[str, str] = {
    "office": "辦公室營運",
    "vehicle": "車輛管理",
    "equipment": "設備管理",
    "personnel": "人事費用",
    "maintenance": "維修保養",
    "misc": "雜項",
}

ACCOUNT_CATEGORY_CODES: Dict[str, str] = {
    "office": "OF",
    "vehicle": "VH",
    "equipment": "EQ",
    "personnel": "HR",
    "maintenance": "MT",
    "misc": "MS",
}

EXPENSE_SUB_CATEGORIES: Dict[str, str] = {
    "rent": "租金",
    "utility": "水電",
    "insurance": "保險",
    "fuel": "油資",
    "repair": "維修",
    "salary": "薪資",
    "other": "其他",
}


# ============================================================================
# Account Schemas
# ============================================================================

class OperationalAccountCreate(BaseModel):
    """建立營運帳目"""
    name: str = Field(..., max_length=200, description="帳目名稱")
    category: str = Field(..., description="類別: office/vehicle/equipment/personnel/maintenance/misc")
    fiscal_year: int = Field(..., description="年度 (西元)")
    budget_limit: Decimal = Field(default=Decimal("0"), max_digits=15, decimal_places=2,
                                  description="年度預算上限")
    department: Optional[str] = Field(None, max_length=100, description="所屬部門")
    owner_id: Optional[int] = Field(None, description="帳目負責人 ID")
    notes: Optional[str] = Field(None, description="備註")


class OperationalAccountUpdate(BaseModel):
    """更新營運帳目"""
    name: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = None
    budget_limit: Optional[Decimal] = Field(None, max_digits=15, decimal_places=2)
    department: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, description="狀態: active/closed/frozen")
    owner_id: Optional[int] = None
    notes: Optional[str] = None


class OperationalAccountUpdateRequest(BaseModel):
    """更新營運帳目請求 (含 id)"""
    id: int
    data: OperationalAccountUpdate


class OperationalAccountListRequest(BaseModel):
    """營運帳目列表查詢"""
    category: Optional[str] = None
    fiscal_year: Optional[int] = None
    status: Optional[str] = None
    keyword: Optional[str] = Field(None, description="名稱/編號模糊搜尋")
    skip: int = 0
    limit: int = Field(default=20, le=100)


class OperationalAccountResponse(BaseModel):
    """營運帳目回應"""
    id: int
    account_code: str
    name: str
    category: str
    category_label: Optional[str] = None
    fiscal_year: int
    budget_limit: Decimal
    department: Optional[str] = None
    status: str
    owner_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    # Computed
    total_spent: Optional[Decimal] = Field(None, description="累計支出")
    budget_usage_pct: Optional[Decimal] = Field(None, description="預算使用率 (%)")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Expense Schemas
# ============================================================================

class OperationalExpenseCreate(BaseModel):
    """建立營運費用"""
    account_id: int = Field(..., description="帳目 ID")
    expense_date: datetime.date = Field(..., description="費用日期")
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2, description="金額")
    description: Optional[str] = Field(None, max_length=500, description="摘要說明")
    category: Optional[str] = Field(None, description="費用分類")
    expense_invoice_id: Optional[int] = Field(None, description="關聯發票 ID")
    asset_id: Optional[int] = Field(None, description="關聯資產 ID")
    notes: Optional[str] = None


class OperationalExpenseListRequest(BaseModel):
    """營運費用列表查詢"""
    account_id: Optional[int] = None
    category: Optional[str] = None
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    approval_status: Optional[str] = None
    skip: int = 0
    limit: int = Field(default=20, le=100)


class OperationalExpenseResponse(BaseModel):
    """營運費用回應"""
    id: int
    account_id: int
    expense_date: datetime.date
    amount: Decimal
    description: Optional[str] = None
    category: Optional[str] = None
    expense_invoice_id: Optional[int] = None
    asset_id: Optional[int] = None
    approval_status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime.datetime] = None
    created_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OperationalExpenseApproveRequest(BaseModel):
    """審批費用請求"""
    id: int


class OperationalExpenseRejectRequest(BaseModel):
    """駁回費用請求"""
    id: int
    reason: Optional[str] = Field(None, max_length=500, description="駁回原因")


# ============================================================================
# Stats Schema
# ============================================================================

class OperationalAccountStatsResponse(BaseModel):
    """營運帳目統計"""
    total_accounts: int = 0
    total_budget: Decimal = Decimal("0")
    total_spent: Decimal = Decimal("0")
    by_category: Dict[str, Dict[str, Decimal]] = Field(
        default_factory=dict,
        description="依類別: {category: {budget, spent}}"
    )
