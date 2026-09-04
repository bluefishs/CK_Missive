"""廠商財務彙總 Schemas

Version: 1.1.0
Created: 2026-03-22
Updated: 2026-03-30 — 新增跨案件帳款查詢 schemas
"""
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 明細子項 (line items)
# ============================================================================

class PayableLineItem(BaseModel):
    """應付明細子項"""
    id: int
    description: Optional[str] = None
    payable_amount: Decimal = Decimal("0")
    paid_amount: Decimal = Decimal("0")
    payment_status: str = "unpaid"
    due_date: Optional[str] = None
    paid_date: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class BillingLineItem(BaseModel):
    """請款明細子項"""
    id: int
    billing_period: Optional[str] = None
    billing_date: Optional[str] = None
    billing_amount: Decimal = Decimal("0")
    payment_status: str = "pending"
    payment_date: Optional[str] = None
    payment_amount: Decimal = Decimal("0")
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 跨案件廠商帳款查詢
# ============================================================================

class VendorAccountListRequest(BaseModel):
    """廠商帳款列表查詢"""
    vendor_type: str = Field(default="subcontractor", pattern=r"^(subcontractor|client)$")
    year: Optional[int] = None
    keyword: Optional[str] = None
    skip: int = 0
    # 2026-09-04 owner「/erp/client-accounts 表格無法查詢」：委託單位 186 家、預設 50 ⇒ 頁面永遠只有 50 家。
    # 彙總是每家一列，上限放到 1000（weekly 95 家族：上限壞在資料長過它的那天——頁面另有截斷警示）。
    limit: int = Field(50, ge=1, le=1000)


class ClientAccountListRequest(BaseModel):
    """委託單位帳款列表查詢"""
    year: Optional[int] = None
    keyword: Optional[str] = None
    skip: int = 0
    # 2026-09-04 owner「/erp/client-accounts 表格無法查詢」：委託單位 186 家、預設 50 ⇒ 頁面永遠只有 50 家。
    # 彙總是每家一列，上限放到 1000（weekly 95 家族：上限壞在資料長過它的那天——頁面另有截斷警示）。
    limit: int = Field(50, ge=1, le=1000)


class VendorAccountSummaryItem(BaseModel):
    """廠商帳款彙總項目 (列表用)"""
    vendor_id: int
    vendor_name: str
    vendor_code: Optional[str] = None
    tax_id: Optional[str] = Field(None, description="統一編號（2026-09-04 起 vendor_code 只當內部代碼）")
    case_count: int = 0
    total_payable: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
    model_config = ConfigDict(from_attributes=True)


class VendorAccountDetailRequest(BaseModel):
    """單一廠商帳款明細查詢"""
    vendor_id: int
    year: Optional[int] = None


class VendorCasePayableItem(BaseModel):
    """廠商在單一案件的應付明細"""
    erp_quotation_id: int
    case_code: str
    case_name: Optional[str] = None
    year: Optional[int] = None
    payable_amount: Decimal = Decimal("0")
    paid_amount: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
    payment_status: str = "unpaid"
    items: List[PayableLineItem] = []
    model_config = ConfigDict(from_attributes=True)


class VendorAccountDetail(BaseModel):
    """單一廠商完整帳款"""
    vendor_id: int
    vendor_name: str
    vendor_code: Optional[str] = None
    tax_id: Optional[str] = Field(None, description="統一編號（2026-09-04 起 vendor_code 只當內部代碼）")
    total_payable: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
    cases: List[VendorCasePayableItem] = []
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 單一廠商財務彙總 (既有)
# ============================================================================

class ClientAccountSummaryItem(BaseModel):
    """委託單位帳款彙總項目 (列表用)"""
    # None＝客戶只存在於承攬案件文字欄，尚無 partner_vendor 主檔
    # （2026-08-28 彙總腿 2；與 frontend/src/types/erp.ts 同步）
    vendor_id: Optional[int] = None
    vendor_name: str
    vendor_code: Optional[str] = None
    tax_id: Optional[str] = Field(None, description="統一編號（2026-09-04 起 vendor_code 只當內部代碼）")
    case_count: int = 0
    total_contract: Decimal = Decimal("0")  # total_price from quotations
    total_billed: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
    model_config = ConfigDict(from_attributes=True)


class ClientCaseReceivableItem(BaseModel):
    """委託單位在單一案件的應收明細"""
    # None＝該案尚未建報價單（零額列，2026-08-28 起不再整案消失；
    # 與 frontend/src/types/erp.ts 同步）
    erp_quotation_id: Optional[int] = None
    case_code: str
    case_name: Optional[str] = None
    year: Optional[int] = None
    contract_amount: Decimal = Decimal("0")
    total_billed: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
    items: List[BillingLineItem] = []
    model_config = ConfigDict(from_attributes=True)


class ClientAccountDetail(BaseModel):
    """單一委託單位完整帳款"""
    vendor_id: int
    vendor_name: str
    vendor_code: Optional[str] = None
    tax_id: Optional[str] = Field(None, description="統一編號（2026-09-04 起 vendor_code 只當內部代碼）")
    total_contract: Decimal = Decimal("0")
    total_billed: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
    cases: List[ClientCaseReceivableItem] = []
    model_config = ConfigDict(from_attributes=True)


class VendorFinancialSummary(BaseModel):
    """廠商財務彙總"""
    vendor_id: int
    vendor_name: str
    vendor_code: Optional[str] = None

    # 應付帳款
    total_payable: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    pending_payable: Decimal = Decimal("0")
    payable_count: int = 0

    # 報銷發票 (透過 seller_ban 配對)
    total_expenses: Decimal = Decimal("0")
    expense_count: int = 0

    # 帳本 (直接 vendor_id 關聯)
    ledger_expense_total: Decimal = Decimal("0")
    ledger_entry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class VendorFinancialSummaryRequest(BaseModel):
    """廠商財務彙總查詢"""
    vendor_id: int
    year: Optional[int] = None
