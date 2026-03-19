"""PM 模組 API 請求 Schemas (SSOT)

所有 PM 端點的 BaseModel 請求定義集中於此，
禁止在 api/endpoints/ 中定義本地 BaseModel。
"""
from typing import Optional
from pydantic import BaseModel, Field

from .case import PMCaseUpdate
from .milestone import PMMilestoneUpdate
from .staff import PMCaseStaffUpdate


# ============================================================================
# 共用 ID 請求
# ============================================================================

class PMIdRequest(BaseModel):
    """通用 PM ID 請求"""
    id: int


class PMCaseIdByFieldRequest(BaseModel):
    """以 pm_case_id 查詢的請求 (人員/里程碑列表)"""
    pm_case_id: int


# ============================================================================
# 案件請求
# ============================================================================

class PMCaseIdRequest(BaseModel):
    """案件 ID 請求"""
    id: int


class PMCaseUpdateRequest(BaseModel):
    """案件更新請求 (POST body 包含 id + data)"""
    id: int
    data: PMCaseUpdate


class PMSummaryRequest(BaseModel):
    """案件統計摘要/匯出請求"""
    year: Optional[int] = Field(None, description="年度")


class PMGenerateCodeRequest(BaseModel):
    """產生 PM 案號請求"""
    year: int = Field(..., description="年度 (民國年或西元年)")
    category: str = Field("01", description="類別代碼")


class PMCrossLookupRequest(BaseModel):
    """跨模組案號查詢請求"""
    case_code: str = Field(..., description="統一案號")


class PMLinkedDocsRequest(BaseModel):
    """案號關聯公文查詢請求"""
    case_code: str = Field(..., description="案號")
    limit: int = Field(20, description="最多回傳筆數")


# ============================================================================
# 人員請求
# ============================================================================

class PMStaffUpdateRequest(BaseModel):
    """案件人員更新請求"""
    id: int
    data: PMCaseStaffUpdate


# ============================================================================
# 里程碑請求
# ============================================================================

class PMMilestoneUpdateRequest(BaseModel):
    """里程碑更新請求"""
    id: int
    data: PMMilestoneUpdate
