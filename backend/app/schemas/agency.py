"""
Pydantic schemas for Government Agencies
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class AgencyBase(BaseModel):
    """所有 Agency schema 的基礎模型，定義通用欄位"""
    agency_name: str = Field(..., max_length=200)
    agency_short_name: Optional[str] = Field(None, max_length=100, description="機關簡稱")
    agency_code: Optional[str] = Field(None, max_length=50)
    agency_type: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(from_attributes=True)

class AgencyCreate(AgencyBase):
    """用於新增機關單位的 schema"""
    pass # 直接繼承 AgencyBase 的所有欄位

class AgencyUpdate(BaseModel):
    """用於更新機關單位的 schema，所有欄位皆為可選"""
    agency_name: Optional[str] = Field(None, max_length=200)
    agency_short_name: Optional[str] = Field(None, max_length=100, description="機關簡稱")
    agency_code: Optional[str] = Field(None, max_length=50)
    agency_type: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=100)

class Agency(AgencyBase):
    """用於 API 回應的 schema，包含資料庫生成的欄位"""
    id: int
    created_at: datetime
    updated_at: datetime

class AgencyWithStats(AgencyBase):
    """包含統計資訊的機關 schema"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    document_count: int = 0
    sent_count: int = 0
    received_count: int = 0
    last_activity: Optional[datetime] = None
    primary_type: str = "unknown"  # 'sender', 'receiver', 'both', 'unknown'
    category: str = "政府機關"  # 機關分類
    original_names: Optional[List[str]] = None

class CategoryStat(BaseModel):
    """分類統計 schema"""
    category: str
    count: int
    percentage: float

class AgencyStatistics(BaseModel):
    """機關統計資訊 schema"""
    total_agencies: int
    categories: List[CategoryStat]

class AgenciesResponse(BaseModel):
    """機關列表回應 schema"""
    agencies: List[AgencyWithStats]
    total: int
    returned: int
    search: Optional[str] = None


# =============================================================================
# 查詢與回應 Schema（統一定義，供 endpoints 匯入）
# =============================================================================

class SortOrder(str):
    """排序方向"""
    ASC = "asc"
    DESC = "desc"


class AgencyListQuery(BaseModel):
    """機關列表查詢參數（統一格式）"""
    page: int = Field(default=1, ge=1, description="頁碼")
    limit: int = Field(default=20, ge=1, le=1000, description="每頁筆數")
    search: Optional[str] = Field(None, description="搜尋關鍵字")
    agency_type: Optional[str] = Field(None, description="機關類型")
    include_stats: bool = Field(default=True, description="是否包含統計資料")
    sort_by: str = Field(default="agency_name", description="排序欄位")
    sort_order: str = Field(default="asc", description="排序方向 (asc/desc)")


class AgencyListResponse(BaseModel):
    """機關列表回應 Schema（統一分頁格式）"""
    success: bool = True
    items: List[AgencyWithStats] = Field(default=[], description="機關列表")
    pagination: "PaginationMeta"  # 使用 common.py 中的 PaginationMeta

    model_config = ConfigDict(from_attributes=True)


# PaginationMeta 使用 common.py 中的定義，避免重複
from app.schemas.common import PaginationMeta


# =============================================================================
# 機關建議與關聯 Schema
# =============================================================================

class AgencySuggestRequest(BaseModel):
    """機關建議請求"""
    text: str = Field(..., min_length=2, description="搜尋文字")
    limit: int = Field(default=5, ge=1, le=20, description="回傳數量")


class AgencySuggestResponse(BaseModel):
    """機關建議回應"""
    success: bool = True
    suggestions: List[dict] = []


class AssociationSummary(BaseModel):
    """機關關聯統計"""
    total_documents: int = Field(..., description="公文總數")
    sender_associated: int = Field(..., description="已關聯發文機關")
    sender_unassociated: int = Field(..., description="未關聯發文機關")
    receiver_associated: int = Field(..., description="已關聯受文機關")
    receiver_unassociated: int = Field(..., description="未關聯受文機關")
    association_rate: dict = Field(..., description="關聯率")


class BatchAssociateRequest(BaseModel):
    """批次關聯請求"""
    overwrite: bool = Field(default=False, description="是否覆蓋現有關聯")


class BatchAssociateResponse(BaseModel):
    """批次關聯回應"""
    success: bool
    message: str
    total_documents: int = 0
    sender_updated: int = 0
    receiver_updated: int = 0
    sender_matched: int = 0
    receiver_matched: int = 0
    errors: List[str] = []


# =============================================================================
# 機關資料修復 Schema
# =============================================================================

class FixAgenciesRequest(BaseModel):
    """修復機關資料請求"""
    dry_run: bool = Field(default=True, description="乾跑模式（預設 true，不實際修改）")


class FixAgenciesResponse(BaseModel):
    """修復機關資料回應"""
    success: bool
    message: str
    fixed_count: int = 0
    details: List[dict] = []
