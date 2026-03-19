"""ERP 模組 API 請求 Schemas (SSOT)

所有 ERP 端點的 BaseModel 請求定義集中於此，
禁止在 api/endpoints/ 中定義本地 BaseModel。
"""
from typing import Optional
from pydantic import BaseModel, Field

from .quotation import ERPQuotationUpdate
from .vendor_payable import ERPVendorPayableUpdate
from .billing import ERPBillingUpdate
from .invoice import ERPInvoiceUpdate


# ============================================================================
# 共用 ID 請求
# ============================================================================

class ERPIdRequest(BaseModel):
    """通用 ERP ID 請求"""
    id: int


class ERPQuotationIdRequest(BaseModel):
    """以 erp_quotation_id 查詢的請求 (廠商應付/請款/發票列表)"""
    erp_quotation_id: int


# ============================================================================
# 報價請求
# ============================================================================

class ERPQuotationUpdateRequest(BaseModel):
    """報價更新請求"""
    id: int
    data: ERPQuotationUpdate


class ERPSummaryRequest(BaseModel):
    """損益摘要/匯出請求"""
    year: Optional[int] = Field(None, description="年度")


class ERPGenerateCodeRequest(BaseModel):
    """產生 ERP 案號請求"""
    year: int = Field(..., description="年度 (民國年或西元年)")
    category: str = Field("01", description="類別代碼")


# ============================================================================
# 廠商應付請求
# ============================================================================

class ERPPayableUpdateRequest(BaseModel):
    """廠商應付更新請求"""
    id: int
    data: ERPVendorPayableUpdate


# ============================================================================
# 請款請求
# ============================================================================

class ERPBillingUpdateRequest(BaseModel):
    """請款更新請求"""
    id: int
    data: ERPBillingUpdate


# ============================================================================
# 發票請求
# ============================================================================

class ERPInvoiceUpdateRequest(BaseModel):
    """發票更新請求"""
    id: int
    data: ERPInvoiceUpdate
